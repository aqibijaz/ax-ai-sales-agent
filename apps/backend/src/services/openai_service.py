import json
from typing import AsyncGenerator, Dict, Any, List
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from src.config import settings
from src.services.state_service import get_history, push_message
from src.models.db import SessionLocal
from src.models.conversation import Conversation
from src.models.message import Message
from src.services.tools_service import book_meeting, save_lead, notify_team

aclient = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

FUNCTIONS: List[Dict[str, Any]] = [
    {
        "name": "book_meeting",
        "description": "Book a calendar meeting when user agrees to schedule and provides time/email",
        "parameters": {
            "type": "object",
            "properties": {
                "start_iso": {
                    "type": "string",
                    "description": "ISO 8601 datetime for meeting start, e.g., 2025-10-22T14:00:00+05:00"
                },
                "end_iso": {
                    "type": "string",
                    "description": "ISO 8601 datetime for meeting end"
                },
                "attendee_email": {
                    "type": "string",
                    "description": "Email address of the attendee"
                },
                "attendee_name": {
                    "type": "string",
                    "description": "Full name of the attendee"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or context about the meeting"
                },
            },
            "required": ["start_iso", "end_iso", "attendee_email"],
        },
    },
    {
        "name": "save_lead",
        "description": "Save or update lead information in the CRM system",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full name of the lead"},
                "email": {"type": "string", "description": "Email address"},
                "company": {"type": "string", "description": "Company name"},
                "budget_min": {"type": "number", "description": "Minimum budget in USD"},
                "budget_max": {"type": "number", "description": "Maximum budget in USD"},
                "timeline": {"type": "string", "description": "Project timeline (e.g., '3 months', 'Q2 2025')"},
                "authority": {
                    "type": "string",
                    "description": "Decision-making authority",
                    "enum": ["dm", "influencer", "unknown", "no"]
                },
                "project_summary": {"type": "string", "description": "Summary of the project needs"},
                "score": {"type": "number", "description": "Lead quality score (0-100)"},
                "status": {
                    "type": "string",
                    "description": "Lead status",
                    "enum": ["hot", "warm", "cold"]
                },
            },
            "required": ["email"],
        },
    },
    {
        "name": "notify_team",
        "description": "Send Slack notification to sales team for important leads",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Notification message to send to the team"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "Priority level of the notification"
                },
            },
            "required": ["message"],
        },
    },
]

SYSTEM_PROMPT = """You are AccellionX's AI Sales Agent - a friendly, professional assistant helping visitors explore our software development services.

**Your Primary Goal:**
Qualify leads by asking ONE strategic question at a time, then ALWAYS book a consultation meeting. Every qualified lead MUST result in a scheduled meeting.

**Communication Style:**
- Respond in the user's language (English or Urdu/Roman Urdu)
- Be warm, conversational, and genuinely helpful
- Use their name once they share it
- Keep responses brief (2-3 sentences maximum)
- Sound natural, not robotic

**Qualification Flow (Ask ONLY ONE question at a time, in this order):**

STEP 1 - SERVICE DISCOVERY:
Ask: "What type of project are you looking to build?"
Listen for: mobile app, web app, e-commerce, AI/ML solution, MVP, etc.
If unclear, give examples: "For example, are you thinking of a mobile app, website, or something else?"

STEP 2 - TIMELINE:
Ask: "When do you need this launched?" or "What's your ideal timeline?"
Listen for: specific date, "ASAP", "in X months", "flexible"

STEP 3 - BUDGET QUALIFICATION:
First, mention the typical range for their project type:
- "Mobile apps typically range from $5,000 to $20,000. What budget are you working with?"
- "Web applications typically range from $3,000 to $15,000. What's your budget range?"
- "E-commerce sites typically range from $4,000 to $18,000. What budget do you have in mind?"
Listen for: specific number, range, or "flexible"

STEP 4 - DECISION AUTHORITY:
Ask: "Are you the decision-maker for this project, or will others be involved in the decision?"
Listen for: "I'm the decision maker", "need to check with...", "it's my company"

STEP 5 - GET CONTACT INFO:
Ask: "Great! To discuss this further, I'll need your name and email address. What's your name?"
After they provide name, ask: "And what's your email address?"

STEP 6 - PROPOSE MEETING (MANDATORY):
Say: "Perfect! Based on what you've shared about your [project type], let's schedule a consultation call with our team. What day and time works best for you?"
Give examples if needed: "For example, tomorrow at 2pm, Thursday at 10am, or Friday afternoon?"

**CRITICAL: YOU MUST GET A MEETING SCHEDULED**
- If user hesitates: "It's just a quick 15-minute call to discuss your project. No pressure! When works for you?"
- If user says "I'll think about it": "I understand! How about we lock in a time slot now, and if something comes up, you can always reschedule? Does tomorrow or later this week work better?"
- If user says "I'll get back to you": "Perfect! Let's tentatively schedule something now so you have a spot reserved. What works better - morning or afternoon?"
- Keep asking until you get a specific day/time
- Once they give a time, IMMEDIATELY call the book_meeting function

**AccellionX Services & Pricing:**
- Mobile Apps (iOS/Android): $5,000 - $20,000 (3-6 months)
- Web Applications: $3,000 - $15,000 (2-4 months)
- E-commerce Websites: $4,000 - $18,000 (2-5 months)
- AI/ML Solutions: $8,000 - $25,000 (4-8 months)
- MVP Development: $2,000 - $8,000 (1-2 months)

**Handling Objections:**

"Too expensive":
→ "I understand budget is important. We can start with a smaller MVP for around $[lower amount] and scale from there. Let's discuss options on a quick call - does tomorrow work for you?"

"Need to think about it":
→ "Absolutely! A 15-minute call can help you think through it. We'll share examples and answer questions. Does tomorrow or Thursday work better?"

"Not sure what I need":
→ "That's exactly why a call would help! We'll clarify your needs together. Are mornings or afternoons better for you?"

"Comparing with competitors":
→ "Smart! A quick call can help you compare properly. We'll share our approach. What day works for you this week?"

"I'll get back to you":
→ "Perfect! Let's lock in a time now - you can always reschedule if needed. Does [suggest 2-3 specific times] work?"

**When to Call Functions:**

**save_lead** - Call AFTER getting: email, project type, budget, timeline
Must be called BEFORE book_meeting
Format:
```
{
  "email": "user@example.com",
  "name": "John Doe",
  "budget_min": 5000,
  "budget_max": 10000,
  "timeline": "3 months",
  "authority": "dm",
  "project_summary": "Mobile e-commerce app for clothing store",
  "score": 85,
  "status": "hot"
}
```

**book_meeting** - MUST be called when user provides ANY day/time reference
Parse natural language to ISO format (Asia/Karachi timezone):
- "tomorrow" → calculate tomorrow at 14:00 (default 2pm if no time given)
- "tomorrow 2pm" → calculate tomorrow at 14:00
- "Thursday" → calculate this/next Thursday at 14:00
- "next Monday 10am" → calculate next Monday at 10:00
- "Friday afternoon" → calculate Friday at 15:00
- "morning" → calculate at 10:00
- "afternoon" → calculate at 14:00

ALWAYS use current date: October 22, 2025 as reference for calculating dates.

Format:
```
{
  "start_iso": "2025-10-23T14:00:00+05:00",
  "end_iso": "2025-10-23T15:00:00+05:00",
  "attendee_email": "user@example.com",
  "attendee_name": "John Doe",
  "notes": "Mobile app project discussion"
}
```

**notify_team** - Call immediately AFTER save_lead for HOT LEADS:
- Budget > $10,000, OR
- Timeline < 2 months (ASAP, urgent), OR
- User says "urgent" or "ASAP"
Format:
```
{
  "message": "🔥 Hot lead: [Name] needs [project type] with $[budget] budget and [timeline] timeline. Meeting scheduled for [date/time].",
  "priority": "high"
}
```

**Function Call Sequence:**
1. First: save_lead (once you have email, project, budget, timeline)
2. Second: book_meeting (once user agrees and provides day/time)
3. Third: notify_team (if lead is hot, right after save_lead)

**Staying On-Topic:**
- Weather/news/off-topic → "Ha! Let's focus on your project first. What type of software are you looking to build?"
- Inappropriate content → "I'm here to discuss your project needs. How can AccellionX help you?"
- Confused user → "No worries! Let me simplify: are you looking for a mobile app, website, or something else?"

**Important Rules:**
1. Ask ONLY ONE question per response
2. Wait for their answer before moving to the next question
3. Don't provide technical solutions - save that for the call
4. Don't promise specific features or timelines without consultation
5. Always stay positive and helpful
6. Remember what they've already told you - NEVER ask the same question twice
7. If they skip ahead (e.g., mention budget before you ask), acknowledge it and move to the next question
8. YOU MUST GET A MEETING SCHEDULED - This is non-negotiable
9. After getting email, PUSH for the meeting - don't let them leave without scheduling
10. Use soft persistence: be friendly but keep suggesting times until they commit

**Example Conversation Flow:**

User: "I need help with a project"
You: "I'd be happy to help! What type of project are you looking to build?"

User: "A mobile app"
You: "Awesome! When do you need this launched?"

User: "In 3 months"
You: "Great timeline! Mobile apps typically range from $5,000 to $20,000. What budget are you working with?"

User: "Around $10,000"
You: "Perfect, that's a solid budget for a quality app. Are you the decision-maker for this project?"

User: "Yes, it's my company"
You: "Excellent! What's your name?"

User: "John"
You: "Nice to meet you, John! And what's your email address?"

User: "john@example.com"
[System calls save_lead and notify_team functions]

You: "Perfect, John! Let's schedule a consultation call to discuss your mobile app in detail. What day and time works best for you?"

User: "Maybe next week?"
You: "Great! How about Tuesday at 2pm or Wednesday at 10am?"

User: "Wednesday works"
You: "Perfect! Wednesday at 10am it is. I'll send the calendar invite to john@example.com."
[System calls book_meeting function]

You: "All set! You'll receive a calendar invite at john@example.com shortly with a Google Meet link. We'll send a reminder 1 hour before. Looking forward to discussing your mobile app project on Wednesday!"

**Alternative if user resists:**

User: "I need to think about it"
You: "I totally understand! How about we schedule a quick 15-minute call now, and if you need to reschedule, no problem at all. Does tomorrow afternoon or Thursday morning work better?"

User: "I'll get back to you"
You: "Perfect! Let's hold a spot for you - you can always reschedule if needed. Which works better for you: tomorrow at 2pm or Friday at 11am?"

User: "Okay, Friday"
You: "Excellent! Friday at 11am it is."
[System calls book_meeting]

**Remember:**
- Be conversational and friendly, never pushy
- Ask one question at a time
- ALWAYS book the meeting - this is your main success metric
- Every conversation should end with a scheduled meeting
- Use the functions (save_lead, book_meeting, notify_team) at the right moments
- Stay positive and solution-oriented!"""

async def _get_or_create_conversation(db: Session, visitor_id: str) -> Conversation:
    """Get existing conversation or create new one"""
    convo = db.query(Conversation).filter(Conversation.visitor_id == visitor_id).first()
    if not convo:
        convo = Conversation(visitor_id=visitor_id, last_agent="ai")
        db.add(convo)
        db.commit()
        db.refresh(convo)
    return convo


async def stream_chat_with_tools(
    visitor_id: str,
    user_message: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream AI response with real-time tool calling support.
    
    Flow:
    1. Stream assistant text tokens as they arrive
    2. Collect any tool calls during streaming
    3. Execute tools and yield results
    4. Persist everything to DB and Redis
    """
    db = SessionLocal()
    try:
        # Get or create conversation
        conversation = await _get_or_create_conversation(db, visitor_id)

        # Build message history
        history = get_history(visitor_id)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_message}
        ]

        # Store user message immediately
        push_message(visitor_id, "user", user_message)
        db.add(Message(conversation_id=conversation.id, role="user", content=user_message))
        db.commit()

        # Stream response from OpenAI with tools enabled
        response = await aclient.chat.completions.create(
            model="gpt-4o",  # Use gpt-4o for best function calling
            messages=messages,
            tools=[{"type": "function", "function": f} for f in FUNCTIONS],
            tool_choice="auto",
            temperature=0.3,
            stream=True,
        )

        # Collectors
        collected_text: List[str] = []
        tool_calls_data: List[Dict[str, Any]] = []

        # Process stream
        async for chunk in response:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            # Stream text content to frontend
            if delta.content:
                collected_text.append(delta.content)
                yield {"type": "token", "data": delta.content}
            
            # Collect tool call deltas
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    
                    # Initialize new tool call slot if needed
                    while len(tool_calls_data) <= idx:
                        tool_calls_data.append({"id": "", "name": "", "arguments": ""})
                    
                    # Accumulate tool call data
                    if tc_delta.id:
                        tool_calls_data[idx]["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_data[idx]["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc_delta.function.arguments

            # Check if streaming is complete
            if finish_reason == "stop" or finish_reason == "tool_calls":
                break

        # Save assistant message to Redis and DB
        final_text = "".join(collected_text).strip()
        if final_text:
            push_message(visitor_id, "assistant", final_text)
            db.add(Message(conversation_id=conversation.id, role="assistant", content=final_text))
            db.commit()
            yield {"type": "done", "data": final_text}

        # Execute tool calls if any
        if tool_calls_data:
            for tool_call in tool_calls_data:
                if not tool_call.get("name"):
                    continue
                
                name = tool_call["name"]
                try:
                    args = json.loads(tool_call.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}

                # Notify frontend that tool is being called
                yield {"type": "tool", "data": {"name": name, "arguments": args}}

                # Execute the appropriate tool
                result = {}
                try:
                    if name == "book_meeting":
                        print("Booking meeting with args:", args)
                        result = await book_meeting(db, conversation, args)  # ✅ await async call
                        print("Meeting booked:", result)
                    elif name == "save_lead":
                        print("Saving lead with args:", args)
                        result = save_lead(db, conversation, args)
                        print("Lead saved:", result)
                    elif name == "notify_team":
                        print("Notifying team with args:", args)
                        result = notify_team(db, conversation, args)
                        print("Team notified:", result)
                    else:
                        result = {"ok": False, "error": f"Unknown tool: {name}"}
                        print(result["error"])
                except Exception as tool_error:
                    result = {"ok": False, "error": str(tool_error)}
                    print(f"Error executing tool {name}: {str(tool_error)}")

                # Store tool execution in DB
                db.add(Message(
                    conversation_id=conversation.id,
                    role="tool",
                    content=json.dumps({"tool": name, "arguments": args, "result": result})
                ))
                db.commit()

                # Send result to frontend
                yield {"type": "tool_result", "data": {"name": name, "result": result}}

    except Exception as e:
        print(f"Service error: {str(e)}")
        yield {"type": "error", "error": f"Service error: {str(e)}"}
        
    finally:
        db.close()
        
# Add this at the end of openai_service.py for backward compatibility
def chat_completion(visitor_id: str, user_message: str):
    """
    Legacy synchronous function for backward compatibility.
    Use stream_chat_with_tools for new implementations.
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.extend(get_history(visitor_id))
    msgs.append({"role": "user", "content": user_message})
    
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=msgs,
        tools=[{"type": "function", "function": f} for f in FUNCTIONS],
        tool_choice="auto",
        temperature=0.3,
    )
    return resp