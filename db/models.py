import os
from pymodm import MongoModel, fields, connect
from pymongo.operations import IndexModel
from pymongo import ASCENDING, DESCENDING
from typing import List
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

connect(MONGODB_URI)


class CustomMongoModel(MongoModel):
    def to_json(self):
        dict_obj = self.to_son().to_dict()
        dict_obj["_id"] = str(dict_obj["_id"])
        return dict_obj


class UserField(fields.CharField):
    required = True


class ObjectID(str):
    pass


class ChatRoom(CustomMongoModel):
    title = fields.CharField(min_length=1, required=True)
    admin = UserField()
    participants = fields.ListField(field=UserField())
    active = fields.BooleanField(default=True)


class ChatRoomInput(BaseModel):
    title: str
    admin: ObjectID
    participants: List[ObjectID]
    active: bool = True


class ChatMessage(CustomMongoModel):
    room = fields.ReferenceField(
        ChatRoom, required=True, on_delete=fields.ReferenceField.CASCADE
    )
    user = UserField()
    time = fields.TimestampField(required=True)

    class Meta:
        indexes = [
            IndexModel(
                keys=[
                    ("time", DESCENDING),
                    ("room", ASCENDING),
                    ("user", ASCENDING),
                ],
                unique=True,
            )
        ]


class ChatMessageInput(BaseModel):
    room: ObjectID
    user: ObjectID
    time: datetime
