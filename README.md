# Hedwig 🦉💬
<img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=darkgreen" /> <img src="https://img.shields.io/badge/Messenger-00B2FF?style=for-the-badge&logo=messenger&logoColor=white" /> <img src="https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white" /> <img src="https://img.shields.io/badge/redis-CC0000.svg?&style=for-the-badge&logo=redis&logoColor=white" /> <img src="https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white" />

**Hedwig, the messenger** is an asynchronus web-server to support chat-applications having multiple rooms/groups, each having two or more participants.

Hedwig is built using [FastAPI](https://fastapi.tiangolo.com/) and [websockets](https://websockets.readthedocs.io/en/stable/). [MongoDB](https://www.mongodb.com/) is used as the persistent storage, whereas [Redis](https://redis.io/) is used as the caching layer for messages - its [Pub/Sub](https://redis.io/topics/pubsub) feature is used for triggering sending/receiving of messages.

### Flow-Diagram
<p align="center">
  <img src="./design/Hedwig.png">
</p>

### Use-Case
Ideal use-case of Hedwig would be when you have to add chat-rooms in various parts of your app or website, which is not chatting platform per se.  
Hedwig opens a new webosocket connection for every chat room. This has been done intentionally so that resources are not wasted (in maintaining websocket-connections) when chatting features are not being used.

## Usage
- Install the dependencies (mentioned in [pyproject.toml](https://github.com/shawarmaKoders/Hedwig/blob/main/pyproject.toml) and [poetry.lock](https://github.com/shawarmaKoders/Hedwig/blob/main/poetry.lock))  
  If you're using [poetry](https://python-poetry.org/), just run `poetry install`
- The project needs a mongoDB server and a Redis server running.  
  Hedwig picks up these environment variables: `MONGODB_URI`, `REDIS_URL`  
  You can also just create a `.env` file and add them like these so you don't have to set them again and again
```
MONGODB_URI=...
REDIS_URL=...
```
- Run the server
```
uvicorn main:app
```
- Create a chat-room by making a POST request on `/chat-room/create`
- Open a websocket connection and chat on `/chat-room/{chat_room_id}/chat?user_id={user_id}`
  - Incoming Messages Format:
    ```json
    {
      "time": timestamp,
      "text": "text message"
    }
    ```
  - Outgoing Messages Format:
    ```json
    {
      "user": "user_id",
      "time": timestamp,
      "text": "text message"
    }
    ```
