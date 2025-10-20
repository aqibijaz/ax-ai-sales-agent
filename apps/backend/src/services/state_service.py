import json
import redis
from src.config import settings

# decode_responses=True makes Redis return str (not bytes)
r = redis.from_url(settings.REDIS_URL, decode_responses=True)

MAX_TURNS = 60  # keep last N turns per visitor


def _key(visitor_id: str) -> str:
    return f"chat:{visitor_id}:history"


def push_message(visitor_id: str, role: str, content: str) -> None:
    """Append a message to the visitor's conversation (FIFO, capped)."""
    item = json.dumps({"role": role, "content": content})
    r.rpush(_key(visitor_id), item)
    r.ltrim(_key(visitor_id), -MAX_TURNS, -1)
    # 24h TTL (optional): keep memory for a day
    r.expire(_key(visitor_id), 60 * 60 * 24)


def get_history(visitor_id: str) -> list[dict]:
    raw = r.lrange(_key(visitor_id), 0, -1)
    return [json.loads(x) for x in raw]


def clear_history(visitor_id: str) -> None:
    r.delete(_key(visitor_id))
