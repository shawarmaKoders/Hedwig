import asyncio

from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from db.models import (
    ChatRoom,
    ChatRoomInput,
    ObjectID,
)
from messaging import PrivateConnectionManager

app = FastAPI()


@app.post("/chat-room/create")
async def create_chat_room(chat_input: ChatRoomInput):
    chat_room = ChatRoom(**dict(chat_input)).save()
    chat_room_response = chat_room.to_json()
    return JSONResponse(chat_room_response, status_code=status.HTTP_201_CREATED)


@app.websocket("/chat-room/{chat_room_id}/chat")
async def chat(websocket: WebSocket, chat_room_id: ObjectID, user_id: ObjectID):
    print(f"{chat_room_id=}, {user_id=}")
    # check if user exists in an active room or not
    try:
        async with PrivateConnectionManager(
            user_id=user_id, chat_room_id=chat_room_id, websocket=websocket
        ) as conn:
            while True:
                data = await websocket.receive_text()
                await conn.send_message(message=data)
                await asyncio.sleep(0)
    except WebSocketDisconnect:
        pass


@app.patch("/chat-room/{chat_room_id}/deactivate")
async def deactivate_chat_room(chat_room_id: ObjectID):
    return JSONResponse({"active": False}, status_code=status.HTTP_200_OK)
