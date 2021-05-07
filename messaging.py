import asyncio
from json import loads, dumps
from typing import Set

from aioredis.client import PubSub
from asgiref.sync import sync_to_async
from fastapi import WebSocket
from pymongo import ASCENDING

from db.models import ObjectID, ChatMessageInput, ChatMessage, json_loads, BsonObjectID
from redis_util import redis, reader


async def get_chat_history(chat_room_id: ObjectID):
    return dumps(
        json_loads(
            list(
                ChatMessage.objects.only("user", "time", "text")
                .raw({"room": BsonObjectID(chat_room_id)})
                .order_by([("time", ASCENDING)])
                .values()
            )
        )
    )


def convert_room_to_channel(chat_room_id: ObjectID):
    return f"channel:{chat_room_id}"


class ConnectionManager:

    save_msg_in_db_tasks: Set[asyncio.Task]
    reader_tasks: Set[asyncio.Task]

    def __init__(self):
        self.save_msg_in_db_tasks = set()
        self.reader_tasks = set()

    async def connect(
        self,
        *,
        user_id: ObjectID,
        chat_room_id: ObjectID,
        websocket: WebSocket,
        pubsub: PubSub,
    ) -> None:
        await websocket.accept()
        chat_history = await get_chat_history(chat_room_id)
        await websocket.send_text(chat_history)

        channel = convert_room_to_channel(chat_room_id)
        await pubsub.subscribe(channel)
        reader_task = asyncio.create_task(
            reader(pubsub, websocket), name=f"Reader Task for {user_id=}"
        )
        self.reader_tasks.add(reader_task)
        reader_task.add_done_callback(self.reader_tasks.discard)

    async def disconnect(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, pubsub: PubSub
    ) -> None:
        channel = convert_room_to_channel(chat_room_id)
        await pubsub.unsubscribe(channel)
        await asyncio.gather(*self.save_msg_in_db_tasks)
        self.save_msg_in_db_tasks.clear()
        for task in self.reader_tasks:
            task.done()

    async def send_message(
        self,
        *,
        user_id: ObjectID,
        chat_room_id: ObjectID,
        message: ChatMessageInput,
    ):
        channel = convert_room_to_channel(chat_room_id)
        channel_message = dumps(
            {
                "user": user_id,
                "time": message.time.timestamp(),
                "text": message.text,
            }
        )
        await redis.publish(channel, channel_message)
        save_chat_msg = sync_to_async(
            ChatMessage(
                user=user_id, room=chat_room_id, text=message.text, time=message.time
            ).save,
            thread_sensitive=True,
        )
        self.save_msg_in_db_tasks.add(
            asyncio.create_task(
                save_chat_msg(),
                name=f"Save Message in DB Task {user_id=} {chat_room_id=}",
            )
        )


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
        print("PrivateConnectionManager - __aexit__")
        await conn_manager.disconnect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            pubsub=self.pubsub,
        )
        await self.pubsub.close()
