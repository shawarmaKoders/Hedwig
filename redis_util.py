import os

import aioredis
from dotenv import load_dotenv
from fastapi import WebSocket

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
# REDIS_PORT = os.getenv('REDIS_PORT')

MAX_CONNECTIONS = 10

redis = aioredis.from_url(
    REDIS_URL, max_connections=MAX_CONNECTIONS, decode_responses=True
)


async def reader(channel: aioredis.client.PubSub, websocket: WebSocket):
    while True:
        message = await channel.get_message(ignore_subscribe_messages=True)
        if message is not None:
            await websocket.send_text(message)
