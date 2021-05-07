# Hedwig

**Hedwig, the messenger** is an asynchronus web-server to support chat-applications having multiple rooms/groups, each having two or more participants.

Hedwig is built using [FastAPI](https://fastapi.tiangolo.com/) and [websockets](https://websockets.readthedocs.io/en/stable/). [MongoDB](https://www.mongodb.com/) is used as the persistent storage, whereas [Redis](https://redis.io/) is used as the caching layer for messages - its [Pub/Sub](https://redis.io/topics/pubsub) feature is used for triggering sending/receiving of messages.
