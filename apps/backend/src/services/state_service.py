import json
import redis
from typing import List, Dict, Optional
from src.config import settings
from src.models.db import SessionLocal
from src.models.conversation import Conversation
from src.models.message import Message

# Initialize Redis connection
r = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Redis key TTL (24 hours)
HISTORY_TTL = 86400


def _key(visitor_id: str) -> str:
    """Generate Redis key for visitor's conversation history"""
    return f"chat:session:{visitor_id}:history"


def get_history(visitor_id: str) -> List[Dict[str, str]]:
    """
    Retrieve conversation history from Redis in OpenAI message format.
    
    Args:
        visitor_id: Unique identifier for the visitor
    
    Returns:
        List of message dictionaries: [{"role": "user", "content": "..."}, ...]
    """
    try:
        data = r.lrange(_key(visitor_id), 0, -1)
        return [json.loads(msg) for msg in data]
    except Exception as e:
        print(f"❌ Error retrieving history for {visitor_id}: {str(e)}")
        return []


def push_message(visitor_id: str, role: str, content: str) -> None:
    """
    Store message in Redis AND mirror to PostgreSQL database.
    Maintains both fast cache (Redis) and persistent storage (DB).
    
    Args:
        visitor_id: Unique identifier for the visitor
        role: Message role ("user", "assistant", "system", "tool")
        content: Message content
    """
    try:
        # Store in Redis for fast retrieval
        message_obj = {"role": role, "content": content}
        key = _key(visitor_id)
        r.rpush(key, json.dumps(message_obj))
        r.expire(key, HISTORY_TTL)  # Auto-expire after 24 hours
        
        # Mirror to PostgreSQL for persistence
        db = SessionLocal()
        try:
            # Get or create conversation
            convo = db.query(Conversation).filter(
                Conversation.visitor_id == visitor_id
            ).first()
            
            if not convo:
                convo = Conversation(visitor_id=visitor_id, last_agent="ai")
                db.add(convo)
                db.commit()
                db.refresh(convo)
            
            # Add message to database
            db_message = Message(
                conversation_id=convo.id,
                role=role,
                content=content
            )
            db.add(db_message)
            db.commit()
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error storing message for {visitor_id}: {str(e)}")


def clear_history(visitor_id: str) -> bool:
    """
    Clear conversation history from Redis (DB remains intact for records).
    Useful for starting fresh conversations.
    
    Args:
        visitor_id: Unique identifier for the visitor
    
    Returns:
        bool: True if successful
    """
    try:
        r.delete(_key(visitor_id))
        return True
    except Exception as e:
        print(f"❌ Error clearing history for {visitor_id}: {str(e)}")
        return False


def get_history_length(visitor_id: str) -> int:
    """
    Get the number of messages in conversation history.
    
    Args:
        visitor_id: Unique identifier for the visitor
    
    Returns:
        int: Number of messages
    """
    try:
        return r.llen(_key(visitor_id))
    except Exception:
        return 0


def get_last_message(visitor_id: str, role: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Get the last message from conversation, optionally filtered by role.
    
    Args:
        visitor_id: Unique identifier for the visitor
        role: Optional role filter ("user", "assistant", etc.)
    
    Returns:
        Message dict or None
    """
    try:
        history = get_history(visitor_id)
        if not history:
            return None
        
        if role:
            # Find last message with matching role
            for msg in reversed(history):
                if msg.get("role") == role:
                    return msg
            return None
        else:
            # Return last message regardless of role
            return history[-1]
            
    except Exception as e:
        print(f"❌ Error getting last message for {visitor_id}: {str(e)}")
        return None


def trim_history(visitor_id: str, max_messages: int = 50) -> bool:
    """
    Trim conversation history to prevent Redis from growing too large.
    Keeps only the most recent N messages.
    
    Args:
        visitor_id: Unique identifier for the visitor
        max_messages: Maximum number of messages to keep
    
    Returns:
        bool: True if successful
    """
    try:
        key = _key(visitor_id)
        current_length = r.llen(key)
        
        if current_length > max_messages:
            # Keep only last max_messages
            r.ltrim(key, -max_messages, -1)
            print(f"✂️ Trimmed history for {visitor_id}: {current_length} -> {max_messages}")
        
        return True
    except Exception as e:
        print(f"❌ Error trimming history for {visitor_id}: {str(e)}")
        return False


def get_conversation_summary(visitor_id: str) -> Dict[str, any]:
    """
    Get summary statistics about a conversation.
    
    Args:
        visitor_id: Unique identifier for the visitor
    
    Returns:
        Dictionary with conversation stats
    """
    try:
        history = get_history(visitor_id)
        
        user_messages = [msg for msg in history if msg.get("role") == "user"]
        assistant_messages = [msg for msg in history if msg.get("role") == "assistant"]
        
        return {
            "total_messages": len(history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "avg_user_length": sum(len(msg.get("content", "")) for msg in user_messages) / len(user_messages) if user_messages else 0,
            "avg_assistant_length": sum(len(msg.get("content", "")) for msg in assistant_messages) / len(assistant_messages) if assistant_messages else 0,
        }
    except Exception as e:
        print(f"❌ Error getting conversation summary for {visitor_id}: {str(e)}")
        return {}