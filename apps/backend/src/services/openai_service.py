import json
from typing import AsyncGenerator, Dict, Any, List, Optional

from openai import OpenAI, AsyncOpenAI
from src.config import settings
from src.services.state_service import get_history, push_message

client = OpenAI(api_key=settings.OPENAI_API_KEY)
aclient = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# ----- Functions (tools) schema -----
FUNCTIONS: List[Dict[str, Any]] = [
    {
        "name": "book_meeting",
        "description": "Create a calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                "start_iso": {"type": "string"},
                "end_iso": {"type": "string"},
                "attendee_email": {"type": "string"},
                "attendee_name": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["start_iso", "end_iso", "attendee_email"],
        },
    },
    {
        "name": "save_lead",
        "description": "Upsert a lead in DB/CRM",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "company": {"type": "string"},
                "budget_min": {"type": "number"},
                "budget_max": {"type": "number"},
                "timeline": {"type": "string"},
                "authority": {"type": "string"},
                "project_summary": {"type": "string"},
                "score": {"type": "number"},
                "status": {"type": "string"},
            },
        },
    },
    {
        "name": "notify_team",
        "description": "Slack ping with lead summary",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["message"],
        },
    },
]

SYSTEM_PROMPT = """
You are AccellionX’s AI Sales Agent. Reply in the user's language (English or Urdu/roman-Urdu).
Your primary objective is to first clearly understand what type of service the visitor is looking for. 
Do NOT ask about budget, timeline, or decision-maker until you have fully understood the service they need.

Once the service type is clear, proceed step-by-step — asking only one question at a time — in the following order:
1. Confirm the exact service or solution they are interested in (e.g., website development, mobile app, SaaS platform, AI solution, automation, etc.).
2. Then ask about their budget range.
3. Then ask about their expected timeline.
4. Finally, ask who the decision-maker is.

Keep your questions conversational, natural, and human-like. 
After gathering all details, summarize the project and propose scheduling a meeting.

If the user gives a specific time (e.g., "tomorrow 2pm"), call `book_meeting` with ISO datetime (Asia/Karachi).
If they go off-topic, politely steer the conversation back to business.
Always be concise, professional, and proactive — but never rush through the questions.
IMPORTANT: Do NOT ask more than one question in a single message. If you need multiple pieces of information, ask them one by one in separate turns.
"""



# ==============
# POST (non-stream) API uses this
# ==============
def build_messages(visitor_id: str, user_message: str) -> List[Dict[str, str]]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs.extend(get_history(visitor_id))
    msgs.append({"role": "user", "content": user_message})
    return msgs


def chat_completion(visitor_id: str, user_message: str):
    msgs = build_messages(visitor_id, user_message)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs,
        tools=[{"type": "function", "function": f} for f in FUNCTIONS],
        tool_choice="auto",
        temperature=0.3,
    )
    return resp


# ==============
# WebSocket (stream) API uses this
# ==============
async def stream_chat_text_then_tools(
    visitor_id: str, user_message: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    1) Stream assistant text token-by-token (for UX).
    2) After text ends, run a tiny non-stream call to see if model wants any tool call(s).
    3) If yes, emit 'tool' events with parsed arguments (the HTTP route can execute or we can execute here).
    4) Store the assistant final text in the session history.
    """
    # Build prompt with history
    history = get_history(visitor_id)
    print(f"Chat messages from {visitor_id}: {history}")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": user_message}]

    # --- Stream assistant content first ---
    collected_text_parts: List[str] = []
    try:
        stream = await aclient.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content_piece = getattr(delta, "content", "") or ""
            if content_piece:
                collected_text_parts.append(content_piece)
                yield {"type": "token", "data": content_piece}
    except Exception as ex:
        yield {"type": "error", "error": f"stream_error: {ex}"}
        return

    # Full assistant message
    final_text = "".join(collected_text_parts).strip() or "..."
    push_message(visitor_id, "assistant", final_text)
    yield {"type": "done", "data": final_text}

    # --- SECOND PASS: ask model if it wants to call tools (non-stream, fast) ---
    try:
        resp = await aclient.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages + [{"role": "assistant", "content": final_text}],
            tools=[{"type": "function", "function": f} for f in FUNCTIONS],
            tool_choice="auto",
            temperature=0.0,
            max_tokens=1,  # nudge the model to reveal tool intent without extra text
        )

        choice = resp.choices[0]
        msg = choice.message
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            name = tc.function.name
            args = tc.function.arguments or "{}"
            parsed = json.loads(args)
            # We don't execute here (so sockets stay snappy).
            # The HTTP POST route already handles real execution, but we expose intent to the UI:
            yield {"type": "tool", "data": {"name": name, "arguments": parsed}}
    except Exception:
        # Tool pass is optional; ignore errors here to keep UX smooth
        pass
