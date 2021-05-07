import asyncio
from json import loads
from typing import List

from aioredis.client import PubSub
from asgiref.sync import sync_to_async
from fastapi import WebSocket

from db.models import ObjectID, ChatMessageInput, ChatMessage
from redis_util import redis, reader


def convert_room_to_channel(chat_room_id: ObjectID):
    return f"channel:{chat_room_id}"


class ConnectionManager:

    save_msg_in_db_tasks: List[asyncio.Task]
    reader_tasks: List[asyncio.Task]

    def __init__(self):
        self.save_msg_in_db_tasks = []
        self.reader_tasks = []

    async def connect(
        self,
        *,
        user_id: ObjectID,
        chat_room_id: ObjectID,
        websocket: WebSocket,
        pubsub: PubSub,
    ) -> None:
        await websocket.accept()

        channel = convert_room_to_channel(chat_room_id)
        print(f"# {user_id=} subscribe to {channel=}")
        await pubsub.subscribe(channel)
        self.reader_tasks.append(asyncio.create_task(reader(pubsub, websocket)))

    async def disconnect(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, pubsub: PubSub
    ) -> None:
        channel = convert_room_to_channel(chat_room_id)
        await pubsub.unsubscribe(channel)
        print(
            f"# TODO: Cancel Tasks: {self.save_msg_in_db_tasks=} {self.reader_tasks=}"
        )

    async def send_message(
        self,
        *,
        user_id: ObjectID,
        chat_room_id: ObjectID,
        message: ChatMessageInput,
    ):
        channel = convert_room_to_channel(chat_room_id)
        channel_message = {"user": user_id, **dict(message)}
        print(f"# TODO: {channel_message=} publish to {channel=}")
        # redis.publish(channel, message)
        save_chat_msg = sync_to_async(
            ChatMessage(
                user=user_id,
                room=chat_room_id,
                text=message.text,
                time=message.time,
            ).save,
            thread_sensitive=True,
        )
        self.save_msg_in_db_tasks.append(asyncio.create_task(save_chat_msg()))


conn_manager = ConnectionManager()


class RoomUserConnection:
    def __init__(self, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket):
        self.user_id: ObjectID = user_id
        self.chat_room: ObjectID = chat_room_id
        self.websocket: WebSocket = websocket

    async def send_message(self, *, message: str):
        chat_message_input = ChatMessageInput(**loads(message))
        await conn_manager.send_message(
            user_id=self.user_id,
            chat_room_id=self.chat_room,
            message=chat_message_input,
        )


class PrivateConnectionManager:

    room_user_connection: RoomUserConnection
    pubsub: PubSub

    def __init__(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket
    ):
        self.room_user_connection = RoomUserConnection(user_id, chat_room_id, websocket)
        self.pubsub = redis.pubsub()

    async def __aenter__(self) -> RoomUserConnection:
        await conn_manager.connect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            websocket=self.room_user_connection.websocket,
            pubsub=self.pubsub,
        )
        return self.room_user_connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await conn_manager.disconnect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            pubsub=self.pubsub,
        )
        await self.pubsub.close()
