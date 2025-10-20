from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import json

from src.services.state_service import push_message
from src.services.openai_service import chat_completion
from src.services.scoring_service import score_lead, status_from_score
from src.models.db import get_db
from src.models.lead import Lead

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

class ChatReq(BaseModel):
    visitor_id: str
    message: str

class SaveLeadArgs(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    company: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    timeline: str | None = None
    authority: str | None = None
    project_summary: str | None = None
    score: int | None = None
    status: str | None = None

@router.post("")
def chat(req: ChatReq, db: Session = Depends(get_db)):
    # record user message
    push_message(req.visitor_id, "user", req.message)

    # call OpenAI (may propose tool calls)
    resp = chat_completion(req.visitor_id, req.message)
    choice = resp.choices[0]
    msg = choice.message

    tool_calls = getattr(msg, "tool_calls", None) or []
    tool_results = []

    for tc in tool_calls:
        name = tc.function.name
        args = tc.function.arguments or "{}"
        parsed = json.loads(args)

        if name == "book_meeting":
            # STUB: Just echo back for now
            tool_results.append({"tool": name, "ok": True, "echo": parsed})

        elif name == "save_lead":
            data = SaveLeadArgs(**parsed)
            # compute score if not provided
            sc = data.score if data.score is not None else score_lead(
                data.budget_max or 0, 60, (data.authority or "unknown"), 12
            )
            st = data.status or status_from_score(sc)

            # upsert by email if available; else create new row
            lead = None
            if data.email:
                lead = db.query(Lead).filter(Lead.email == str(data.email)).first()
            if not lead:
                lead = Lead(email=str(data.email) if data.email else None)

            lead.name = data.name
            lead.company = data.company
            lead.budget_min = data.budget_min
            lead.budget_max = data.budget_max
            lead.timeline = data.timeline
            lead.authority = data.authority
            lead.project_summary = data.project_summary
            lead.score = sc
            lead.status = st

            db.add(lead)
            db.commit()
            db.refresh(lead)

            tool_results.append({"tool": name, "ok": True, "lead_id": str(lead.id), "score": sc, "status": st})

        elif name == "notify_team":
            # STUB: no Slack yet
            tool_results.append({"tool": name, "ok": True, "note": parsed.get("message")})

        else:
            tool_results.append({"tool": name, "ok": False, "error": "Unknown tool"})

    assistant_text = msg.content or "Done."
    push_message(req.visitor_id, "assistant", assistant_text)

    return {"message": assistant_text, "tools": tool_results}
