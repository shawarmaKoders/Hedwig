import asyncio
import warnings
from json import loads, dumps
from typing import Set

from aioredis.client import PubSub
from asgiref.sync import sync_to_async
from fastapi import WebSocket
from loguru import logger
from pydantic.error_wrappers import ValidationError
from pymongo import ASCENDING

from db.models import ObjectID, ChatMessageInput, ChatMessage, json_loads, BsonObjectID
from redis_util import redis, reader


@logger.catch
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
        logger.debug("Websocket Accept")
        await websocket.accept()
        logger.debug("Fetch Chat History")
        chat_history = await get_chat_history(chat_room_id)
        logger.debug("Chat History => Websocket")
        await websocket.send_text(chat_history)

        channel = convert_room_to_channel(chat_room_id)
        logger.debug(f"pubsub.subscribe({channel})")
        await pubsub.subscribe(channel)
        reader_task = asyncio.create_task(
            reader(pubsub, websocket), name=f"Reader Task for {user_id=}"
        )
        logger.debug(f"Current Reader Task: {reader_task}")
        self.reader_tasks.add(reader_task)
        logger.debug(f"All Reader Tasks: {self.reader_tasks}")
        reader_task.add_done_callback(self.reader_tasks.discard)

    async def disconnect(
        self, *, user_id: ObjectID, chat_room_id: ObjectID, pubsub: PubSub
    ) -> None:
        channel = convert_room_to_channel(chat_room_id)
        logger.debug(f"pubsub.unsubscribe({channel})")
        await pubsub.unsubscribe(channel)
        await asyncio.gather(*self.save_msg_in_db_tasks)
        self.save_msg_in_db_tasks.clear()
        for task in self.reader_tasks:
            task.done()
        logger.debug(f"All Save Messages Tasks: {self.save_msg_in_db_tasks}")
        logger.debug(f"All Reader Tasks: {self.reader_tasks}")

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
        logger.debug(f"redis.publish({channel}, {channel_message})")
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
        logger.debug(f"All Save Messages Tasks: {self.save_msg_in_db_tasks}")


conn_manager = ConnectionManager()


class RoomUserConnection:
    def __init__(self, user_id: ObjectID, chat_room_id: ObjectID, websocket: WebSocket):
        self.user_id: ObjectID = user_id
        self.chat_room: ObjectID = chat_room_id
        self.websocket: WebSocket = websocket

    async def send_message(self, *, message: str):
        logger.debug("RoomUserConnection")
        logger.debug(f"{message=}")
        try:
            chat_message_input = ChatMessageInput(**loads(message))
        except ValidationError as validation_exc:
            warnings.warn(validation_exc)
            logger.warning(validation_exc)
        else:
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
        logger.debug("Enter - PrivateConnectionManager")
        await conn_manager.connect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            websocket=self.room_user_connection.websocket,
            pubsub=self.pubsub,
        )
        return self.room_user_connection

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.debug("Exit - PrivateConnectionManager")
        await conn_manager.disconnect(
            user_id=self.room_user_connection.user_id,
            chat_room_id=self.room_user_connection.chat_room,
            pubsub=self.pubsub,
        )
        logger.debug("PrivateConnectionManager - pubsub.close()")
        await self.pubsub.close()
