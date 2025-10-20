from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health_root():
    return {"status": "ok", "ts": datetime.now(timezone.utc).isoformat()}
