from __future__ import annotations
import datetime
import uuid
from enum import Enum
from typing import List
from pydantic import BaseModel


class ApnToken(BaseModel):
    apn_token: str


class User(BaseModel):
    id: int
    username: str
    apn_tokens: List[str]
    is_active: bool
    is_admin: bool

    class Config:
        orm_mode = True


class ServiceBase(BaseModel):
    category: str
    color: str
    owner: str


class ServiceCreate(ServiceBase):
    pass


class Service(ServiceBase):
    id: uuid.UUID

    class Config:
        orm_mode = True


class UserService(Service):
    is_subscribed: bool


class UserUpdateService(BaseModel):
    id: uuid.UUID
    is_subscribed: bool


class NotificationBase(BaseModel):
    title: str
    subtitle: str = ""
    url: str = ""


class NotificationCreate(NotificationBase):
    pass


class Notification(NotificationBase):
    id: int
    timestamp: datetime.datetime
    service_id: uuid.UUID

    class Config:
        orm_mode = True


class UserNotification(Notification):
    is_read: bool


class NotificationStatus(str, Enum):
    read = "read"
    unread = "unread"
    deleted = "deleted"


class UserUpdateNotification(BaseModel):
    id: int
    status: NotificationStatus


class Alert(BaseModel):
    title: str
    subtitle: str


class Aps(BaseModel):
    alert: Alert
    badge: int
    sound: str = "default"


class ApnPayload(BaseModel):
    aps: Aps
