from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import AsyncGenerator
from src.services.state_service import push_message, get_history
from src.services.openai_service import stream_chat_text_then_tools

router = APIRouter(prefix="/ws", tags=["chat-ws"])

# (Optional) in-memory tracker for active connections
active_connections: dict[str, WebSocket] = {}


@router.websocket("/chat/{visitor_id}")
async def chat_socket(websocket: WebSocket, visitor_id: str):
    await websocket.accept()
    active_connections[visitor_id] = websocket

    try:
        while True:
            # Expect: {"message": "..."} from the client
            payload = await websocket.receive_json()
            user_msg = (payload or {}).get("message", "").strip()
            print(f"Received message from {visitor_id}: {user_msg}")
            if not user_msg:
                await websocket.send_json({"type": "error", "error": "Empty message"})
                continue

            # record user message
            push_message(visitor_id, "user", user_msg)

            # stream assistant text (token by token) and then (optionally) tools
            async for event in stream_chat_text_then_tools(visitor_id, user_msg):
                print(f"Sending event to {visitor_id}: {event}")
                # event: {"type": "token" | "done" | "tool" | "error", "data": any}
                await websocket.send_json(event)

            # Mark completion of this round
            await websocket.send_json({"type": "round_complete"})
    except WebSocketDisconnect:
        active_connections.pop(visitor_id, None)
