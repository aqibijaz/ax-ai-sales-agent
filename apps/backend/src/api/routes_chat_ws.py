from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.services.state_service import push_message
from src.services.openai_service import stream_chat_with_tools

router = APIRouter(prefix="/ws", tags=["chat-ws"])
active_connections: dict[str, WebSocket] = {}

@router.websocket("/chat/{visitor_id}")
async def chat_socket(websocket: WebSocket, visitor_id: str):
    await websocket.accept()
    active_connections[visitor_id] = websocket

    try:
        while True:
            payload = await websocket.receive_json()
            user_msg = (payload or {}).get("message", "").strip()
            if not user_msg:
                await websocket.send_json({"type": "error", "error": "Empty message"})
                continue

            push_message(visitor_id, "user", user_msg)

            async for event in stream_chat_with_tools(visitor_id, user_msg):
                await websocket.send_json(event)

            await websocket.send_json({"type": "round_complete"})
    except WebSocketDisconnect:
        active_connections.pop(visitor_id, None)
