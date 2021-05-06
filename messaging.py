import asyncio
from json import loads
from typing import Dict, List

from asgiref.sync import sync_to_async
from fastapi import WebSocket

from db.models import ObjectID, ChatMessageInput, ChatMessage


class ConnectionManager:

    connections: Dict[ObjectID, Dict[ObjectID, List[WebSocket]]]

    def __init__(self):
        self.connections = {}

    async def connect(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket
    ) -> None:
        await websocket.accept()
        print(f"# {user_id=} subscribe to channel={chat_room_id}")
        self.connections[chat_room_id][user_id].append(websocket)

    async def disconnect(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket
    ) -> None:
        # Un-subscription
        self.connections[chat_room_id][user_id].remove(websocket)

    async def send_message(
        self,
        *,
        user_id: ObjectID,
        chat_room_id: ObjectID,
        message: ChatMessageInput,
    ):
        channel = chat_room_id
        print(f"# {user_id=} {message=} publish to {channel=}")
        save_chat_msg = sync_to_async(
            ChatMessage(user=user_id, room=chat_room_id, **dict(message)).save,
            thread_sensitive=True,
        )
        save_in_db_task = asyncio.create_task(save_chat_msg())


conn_manager = ConnectionManager()


class RoomUserConnection:
    def __init__(self, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket):
        self.user_id: ObjectID = user_id
        self.chat_room: ObjectID = chat_room_id
        self.websocket: WebSocket = websocket

    async def send_message(self, *, message: str):
        chat_message_input: ChatMessageInput = loads(message)
        await conn_manager.send_message(
            user_id=self.user_id,
            chat_room_id=self.chat_room,
            message=chat_message_input,
        )


class PrivateConnectionManager:
    def __init__(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket
    ):
        self.room_user_connection = RoomUserConnection(user_id, chat_room_id, websocket)

    async def __aenter__(self) -> RoomUserConnection:
        await conn_manager.connect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            websocket=self.room_user_connection.websocket,
        )
        return self.room_user_connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await conn_manager.disconnect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            websocket=self.room_user_connection.websocket,
        )
