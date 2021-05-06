from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pymongo import ASCENDING

from db.models import (
    ChatRoom,
    ChatRoomInput,
    ChatMessage,
    ObjectID,
    json_loads,
)

app = FastAPI()


async def get_chat_history(chat_room_id: ObjectID):
    return json_loads(
        list(
            ChatMessage.objects.only("user", "time")
            .raw({"room": chat_room_id})
            .order_by([("time", ASCENDING)])
            .values()
        )
    )


@app.post("/chat-room/create")
async def create_chat_room(chat_input: ChatRoomInput):
    chat_room = ChatRoom(**dict(chat_input)).save()
    chat_room_response = chat_room.to_json()
    return JSONResponse(chat_room_response, status_code=status.HTTP_201_CREATED)


@app.patch("/chat-room/{chat_room_id}/deactivate")
async def deactivate_chat_room(chat_room_id: ObjectID):
    return JSONResponse({}, status_code=status.HTTP_200_OK)
