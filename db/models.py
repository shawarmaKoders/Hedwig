import os
from datetime import datetime
from json import loads, JSONEncoder
from typing import List

from bson import ObjectId as BsonObjectID
from bson.errors import InvalidId
from dotenv import load_dotenv
from pydantic import BaseModel
from pymodm import MongoModel, fields, connect
from pymongo import ASCENDING, DESCENDING
from pymongo.operations import IndexModel

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

connect(MONGODB_URI)


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, BsonObjectID):
            return str(o)
        if isinstance(o, datetime):
            return o.timestamp()
        return JSONEncoder.default(self, o)


def json_loads(obj):
    return loads(CustomJSONEncoder().encode(obj))


class CustomMongoModel(MongoModel):
    def to_json(self):
        return json_loads(self.to_son().to_dict())


class UserField(fields.ObjectIdField):
    required = True


class ObjectID(BsonObjectID):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            BsonObjectID(v)
        except InvalidId:
            raise TypeError("ObjectId required")
        return str(v)


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

    class Config:
        arbitrary_types_allowed = True


class ChatMessage(CustomMongoModel):
    room = fields.ReferenceField(
        ChatRoom, required=True, on_delete=fields.ReferenceField.CASCADE
    )
    user = UserField()
    time = fields.DateTimeField(required=True)
    text = fields.CharField(min_length=1)

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
    time: datetime
    text: str
