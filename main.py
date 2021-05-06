from fastapi import FastAPI
from db.models import (
    ChatRoom, ChatRoomInput,
    ChatMessage, ChatMessageInput
)

app = FastAPI()


@app.post("/chat-room/create")
def create_chatroom(chat_input: ChatRoomInput):
    return {}
