import os

import aioredis
import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from loguru import logger

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
# REDIS_PORT = os.getenv('REDIS_PORT')

MAX_CONNECTIONS = 10

redis = aioredis.from_url(
    REDIS_URL, max_connections=MAX_CONNECTIONS, decode_responses=True
)


@logger.catch
async def reader(channel: aioredis.client.PubSub, websocket: WebSocket):
    while True:
        try:
            message = await channel.get_message(ignore_subscribe_messages=True)
            if message is not None:
                logger.debug(f"{message=} => Websocket")
                await websocket.send_text(message["data"])
        except websockets.exceptions.ConnectionClosedOK:
            logger.debug(f"{channel=} - websockets.exceptions.ConnectionClosedOk")
            break
        except aioredis.exceptions.ConnectionError:
            logger.debug(f"{channel=} - aioredis.exceptions.ConnectionError")
            break
