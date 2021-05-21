import asyncio

from fastapi import FastAPI, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from loguru import logger
from pymodm.errors import DoesNotExist

from db.models import ChatRoom, ChatRoomInput, ObjectID
from messaging import PrivateConnectionManager

app = FastAPI()


@app.post("/chat-room/create")
@logger.catch
async def create_chat_room(chat_input: ChatRoomInput):
    chat_room = ChatRoom(**dict(chat_input)).save()
    chat_room_response = chat_room.to_json()
    return JSONResponse(chat_room_response, status_code=status.HTTP_201_CREATED)


@app.get("/chat-room/{chat_room_id}")
@logger.catch
async def chat_room_info(chat_room_id: ObjectID):
    try:
        chat_room = ChatRoom.get_chat_room_json(chat_room_id)
    except DoesNotExist:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND)
    else:
        return JSONResponse(chat_room, status_code=status.HTTP_200_OK)


@app.websocket("/chat-room/{chat_room_id}/chat")
@logger.catch
async def chat(websocket: WebSocket, chat_room_id: ObjectID, user_id: ObjectID):
    logger.info(f"{chat_room_id=}, {user_id=}")
    logger.debug("NOT checking if user exists in the active chat-room or not")
    # TODO: check if user exists in an active room or not
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
@logger.catch
async def deactivate_chat_room(chat_room_id: ObjectID):
    logger.info("No implementation yet")
    return JSONResponse({"active": False}, status_code=status.HTTP_200_OK)
