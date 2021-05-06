from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from db.models import ChatRoom, ChatRoomInput, ChatMessage, ChatMessageInput, ObjectID

app = FastAPI()


@app.post("/chat-room/create")
def create_chat_room(chat_input: ChatRoomInput):
    chat_room = ChatRoom(**dict(chat_input)).save()
    chat_room_response = chat_room.to_json()
    return JSONResponse(chat_room_response, status_code=status.HTTP_201_CREATED)


@app.patch("/chat-room/{chat_room_id}/deactivate")
def deactivate_chat_room(chat_room_id: ObjectID):
    return JSONResponse({}, status_code=status.HTTP_200_OK)
