import os
import json
import requests
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import asyncio

from src.config import settings
from src.models.lead import Lead
from src.models.conversation import Conversation
from src.services.scoring_service import score_lead, status_from_score
from src.services.datetime_parser import parse_natural_datetime, format_datetime_friendly
from src.services.email_service import send_meeting_confirmation


async def book_meeting(db: Session, conversation: Conversation, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Book a meeting on Google Calendar and send confirmation email.
    Safe for async FastAPI — handles Meet creation gracefully.
    """

    start_iso = args.get("start_iso")
    end_iso = args.get("end_iso")
    attendee_email = args.get("attendee_email")
    attendee_name = args.get("attendee_name", "Prospect")
    notes = args.get("notes", "")

    # --- Validate ---
    if not start_iso or not end_iso or not attendee_email:
        return {"ok": False, "error": "Missing required fields: start_iso, end_iso, or attendee_email"}

    # --- Check datetime format ---
    try:
        datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    except ValueError as ve:
        return {"ok": False, "error": f"Invalid datetime format: {ve}"}

    # --- Check credentials file ---
    creds_path = settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
    if not creds_path or not os.path.exists(creds_path):
        print("⚠️ No Google Calendar credentials found — using simulation mode")
        return _simulate_meeting(start_iso, end_iso, attendee_email, attendee_name, notes)

    # --- Load credentials ---
    try:
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
    except Exception as cred_error:
        return {"ok": False, "error": f"Invalid credentials file: {cred_error}"}

    # --- Create Calendar Service ---
    service = build("calendar", "v3", credentials=creds)
    calendar_id = getattr(settings, "GOOGLE_CALENDAR_ID", "primary") or "primary"

    # --- Prepare event body ---
    event_body = {
    "summary": f"Sales Consultation - {attendee_name}",
    "description": (
        f"Project consultation call with {attendee_name}\n"
        f"Email: {attendee_email}\n\n"
        f"Google Meet: https://meet.google.com/new\n"  # ✅ static Meet link fallback
        f"Notes:\n{notes}"
    ),
    "start": {
        "dateTime": start_iso,
        "timeZone": "Asia/Karachi",
    },
    "end": {
        "dateTime": end_iso,
        "timeZone": "Asia/Karachi",
    },
    "attendees": [
        {"email": attendee_email, "displayName": attendee_name},  # ✅ ensures invite email
    ],
    "reminders": {
        "useDefault": False,
        "overrides": [
            {"method": "email", "minutes": 60},
            {"method": "popup", "minutes": 15},
        ],
    },
    "conferenceData": None,  # ✅ prevents "Invalid conference type" error
    }


    try:
        # --- Try Meet link creation first ---
        try:
            event_body["conferenceData"] = {
                "createRequest": {
                    "requestId": f"req-{datetime.now().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates='all',
                conferenceDataVersion=1
            ).execute()
        except Exception as conf_err:
            print(f"⚠️ Meet creation not allowed, retrying without it: {conf_err}")
            event_body.pop("conferenceData", None)
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                sendUpdates='all',
            ).execute()

        event_link = created_event.get("htmlLink", "")
        meet_link = created_event.get("hangoutLink")

        # ✅ Send confirmation email (non-blocking)
        try:
            await send_meeting_confirmation(
                to_email=attendee_email,
                attendee_name=attendee_name,
                meeting_time=start_iso,
                event_link=event_link,
                meet_link=meet_link,
            )
            email_sent = True
        except Exception as e:
            print(f"⚠️ Email send failed: {e}")
            email_sent = False

        print(f"✅ Meeting booked for {attendee_email}")

        return {
            "ok": True,
            "event_id": created_event["id"],
            "event_link": event_link,
            "meet_link": meet_link,
            "start_iso": start_iso,
            "end_iso": end_iso,
            "attendee_email": attendee_email,
            "email_sent": email_sent,
        }

    except Exception as e:
        print(f"❌ Calendar booking failed: {e}")
        return {"ok": False, "error": f"Calendar booking failed: {e}"}


def _simulate_meeting(start_iso, end_iso, attendee_email, attendee_name, notes):
    """Fallback simulation mode when no credentials are configured."""
    return {
        "ok": True,
        "event_id": "demo-event-123",
        "event_link": "https://calendar.google.com/event/demo",
        "meet_link": None,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "attendee_email": attendee_email,
        "attendee_name": attendee_name,
        "message": "Simulation mode — Google Calendar integration disabled.",
    }


def save_lead(db: Session, conversation: Conversation, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save or update lead in database with automatic scoring.
    
    Args:
        name: Full name
        email: Email (required, used as unique identifier)
        company: Company name
        budget_min: Minimum budget
        budget_max: Maximum budget
        timeline: Timeline string (e.g., "3 months")
        authority: "dm", "influencer", "unknown", or "no"
        project_summary: Description of project
        score: Optional manual score (0-100)
        status: Optional manual status ("hot"/"warm"/"cold")
    
    Returns:
        {"ok": True/False, "lead_id": "...", "score": 85, "status": "hot"}
    """
    try:
        email = args.get("email")
        if not email:
            return {"ok": False, "error": "Email is required"}

        # Find or create lead
        lead = db.query(Lead).filter(Lead.email == email).first()
        if not lead:
            lead = Lead(email=email)

        # Update lead fields
        lead.name = args.get("name") or lead.name
        lead.company = args.get("company") or lead.company
        lead.budget_min = args.get("budget_min") or lead.budget_min
        lead.budget_max = args.get("budget_max") or lead.budget_max
        lead.timeline = args.get("timeline") or lead.timeline
        lead.authority = args.get("authority") or lead.authority
        lead.project_summary = args.get("project_summary") or lead.project_summary

        # Calculate score if not provided
        if args.get("score") is not None:
            score = int(args["score"])
        else:
            # Parse timeline to days (simple heuristic)
            timeline_str = (lead.timeline or "").lower()
            if "week" in timeline_str:
                timeline_days = 7 * int(''.join(filter(str.isdigit, timeline_str)) or "4")
            elif "month" in timeline_str:
                timeline_days = 30 * int(''.join(filter(str.isdigit, timeline_str)) or "3")
            else:
                timeline_days = 60  # default
            
            # Calculate score
            score = score_lead(
                budget_max=int(lead.budget_max or 0),
                timeline_days=timeline_days,
                authority=lead.authority or "unknown",
                clarity_score=70  # default clarity
            )

        # Determine status
        if args.get("status"):
            status = args["status"]
        else:
            status = status_from_score(score)

        lead.score = score
        lead.status = status

        db.add(lead)
        db.commit()
        db.refresh(lead)

        # Link lead to conversation
        if conversation.lead_id != lead.id:
            conversation.lead_id = lead.id
            db.add(conversation)
            db.commit()

        return {
            "ok": True,
            "lead_id": str(lead.id),
            "score": score,
            "status": status,
            "email": email
        }

    except Exception as e:
        db.rollback()
        return {"ok": False, "error": f"Lead save failed: {str(e)}"}


def notify_team(db: Session, conversation: Conversation, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send Slack notification to sales team for hot leads.
    
    Args:
        message: Notification message
        priority: "low", "normal", or "high"
    
    Returns:
        {"ok": True/False, "priority": "high"}
    """
    
    # Just for demo/testing
    return {
            "ok": True,
            "priority": "high",
            "timestamp": datetime.now().isoformat()
        }
    try:
        message = args.get("message", "New lead activity")
        priority = args.get("priority", "normal")
        
        # Priority emoji mapping
        emoji_map = {
            "low": "ℹ️",
            "normal": "📋",
            "high": "🔥"
        }
        emoji = emoji_map.get(priority, "📋")
        
        # Build rich Slack message
        slack_payload = {
            "text": f"{emoji} Lead Alert - Priority: {priority.upper()}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} New Lead Alert"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Priority:* {priority.upper()} | *Conversation ID:* {conversation.id} | *Time:* <!date^{int(datetime.now().timestamp())}^{{date_short_pretty}} at {{time}}|{datetime.now()}>"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Conversation"
                            },
                            "url": f"{settings.ADMIN_DASHBOARD_URL}/conversations/{conversation.id}",
                            "style": "primary" if priority == "high" else "default"
                        }
                    ]
                }
            ]
        }
        
        # Send to Slack webhook
        response = requests.post(
            settings.SLACK_WEBHOOK_URL,
            json=slack_payload,
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            return {"ok": False, "error": f"Slack returned {response.status_code}"}

        return {
            "ok": True,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {"ok": False, "error": f"Slack notification failed: {str(e)}"}

def parse_meeting_time_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Wrapper to parse meeting time from user text.
    Can be called by AI when user says something like "tomorrow 2pm"
    
    Returns:
        Tuple of (start_iso, end_iso)
    """
    return parse_natural_datetime(text)