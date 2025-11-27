"""
Natural language datetime parsing for meeting bookings.
Converts phrases like "tomorrow 2pm" into ISO datetime strings.
"""

from datetime import datetime, timedelta
import re
import pytz
from typing import Optional, Tuple


def parse_natural_datetime(
    text: str,
    timezone: str = "Asia/Karachi",
    default_duration_minutes: int = 60
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse natural language datetime into ISO format start and end times.
    
    Args:
        text: Natural language string (e.g., "tomorrow at 2pm", "next Monday 10am")
        timezone: Timezone string (default: Asia/Karachi)
        default_duration_minutes: Default meeting duration
    
    Returns:
        Tuple of (start_iso, end_iso) or (None, None) if parsing fails
    
    Examples:
        "tomorrow 2pm" -> ("2025-10-22T14:00:00+05:00", "2025-10-22T15:00:00+05:00")
        "next Monday at 10am" -> ("2025-10-27T10:00:00+05:00", "2025-10-27T11:00:00+05:00")
    """
    try:
        text = text.lower().strip()
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        # Parse relative day
        target_date = None
        
        if "today" in text:
            target_date = now.date()
        elif "tomorrow" in text:
            target_date = (now + timedelta(days=1)).date()
        elif "day after tomorrow" in text:
            target_date = (now + timedelta(days=2)).date()
        elif "next week" in text:
            target_date = (now + timedelta(weeks=1)).date()
        elif "next monday" in text or "monday" in text:
            days_ahead = 0 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next tuesday" in text or "tuesday" in text:
            days_ahead = 1 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next wednesday" in text or "wednesday" in text:
            days_ahead = 2 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next thursday" in text or "thursday" in text:
            days_ahead = 3 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next friday" in text or "friday" in text:
            days_ahead = 4 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next saturday" in text or "saturday" in text:
            days_ahead = 5 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next sunday" in text or "sunday" in text:
            days_ahead = 6 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = (now + timedelta(days=days_ahead)).date()
        
        # If no relative day found, try parsing specific date formats
        if not target_date:
            # Try "Oct 22", "October 22", "22 Oct", etc.
            date_patterns = [
                r'(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(\d{1,2})',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Parse month and day
                    try:
                        if match.group(1).isdigit():
                            day = int(match.group(1))
                            month_str = match.group(2)
                        else:
                            month_str = match.group(1)
                            day = int(match.group(2))
                        
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        month = month_map[month_str.lower()[:3]]
                        year = now.year
                        
                        # If date is in the past, assume next year
                        test_date = datetime(year, month, day).date()
                        if test_date < now.date():
                            year += 1
                        
                        target_date = datetime(year, month, day).date()
                    except (ValueError, KeyError):
                        pass
        
        if not target_date:
            return None, None
        
        # Parse time
        hour = None
        minute = 0
        
        # Try 24-hour format (14:00, 14:30)
        time_24h = re.search(r'(\d{1,2}):(\d{2})', text)
        if time_24h:
            hour = int(time_24h.group(1))
            minute = int(time_24h.group(2))
        else:
            # Try 12-hour format (2pm, 2:30pm, 10am, 10:30am)
            time_12h = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text, re.IGNORECASE)
            if time_12h:
                hour = int(time_12h.group(1))
                minute = int(time_12h.group(2)) if time_12h.group(2) else 0
                period = time_12h.group(3).lower()
                
                # Convert to 24-hour
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
        
        if hour is None:
            # Default to 10am if no time specified
            hour = 10
            minute = 0
        
        # Create start datetime
        start_dt = tz.localize(datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute)))
        
        # Create end datetime (add duration)
        end_dt = start_dt + timedelta(minutes=default_duration_minutes)
        
        # Convert to ISO format
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        
        return start_iso, end_iso
        
    except Exception as e:
        print(f"❌ Datetime parsing error: {str(e)}")
        return None, None


def format_datetime_friendly(iso_string: str) -> str:
    """
    Convert ISO datetime to friendly format.
    
    Args:
        iso_string: ISO 8601 datetime string
    
    Returns:
        Friendly string like "Monday, October 22 at 2:00 PM PKT"
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%A, %B %d at %I:%M %p %Z")
    except Exception:
        return iso_string