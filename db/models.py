from pymodm import MongoModel, fields
from pymongo.operations import IndexModel
from pymongo import ASCENDING, DESCENDING
from typing import List
from datetime import datetime
from pydantic import BaseModel


class UserField(fields.CharField):
    required = True


class ObjectID(str):
    pass


class ChatRoom(MongoModel):
    title = fields.CharField(min_length=1, required=True)
    admin = UserField()
    participants = fields.ListField(field=UserField())
    active = fields.BooleanField(default=True)


class ChatRoomInput(BaseModel):
    title: str
    admin: ObjectID
    participants: List[ObjectID]
    active: bool = True


class ChatMessage(MongoModel):
    room = fields.ReferenceField(ChatRoom, required=True)
    user = UserField()
    time = fields.TimestampField(required=True)

    class Meta:
        indexes = [
            IndexModel(
                keys=[
                    ('time', DESCENDING),
                    ('room', ASCENDING),
                    ('user', ASCENDING),
                ],
                unique=True
            )
        ]


class ChatMessageInput(BaseModel):
    room: ObjectID
    user: ObjectID
    time: datetime
