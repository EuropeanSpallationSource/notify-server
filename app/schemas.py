from __future__ import annotations
import datetime
import re
import uuid
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, validator

RE_COLOR = re.compile(r"^[0-9a-fA-F]{6}$")


def validate_color(color: str) -> str:
    if RE_COLOR.match(color) is None:
        raise ValueError("Color should match [0-9a-fA-F]{6}")
    return color


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class ApnToken(BaseModel):
    apn_token: str


class DeviceToken(BaseModel):
    device_token: str


class UserV1(BaseModel):
    id: int
    username: str
    apn_tokens: List[str]
    is_active: bool
    is_admin: bool


class User(BaseModel):
    id: int
    username: str
    device_tokens: List[str]
    is_active: bool
    is_admin: bool

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    is_active: Optional[bool]
    is_admin: Optional[bool]


class ServiceBase(BaseModel):
    category: str
    color: str
    owner: str

    _validate_color = validator("color", allow_reuse=True)(validate_color)


class ServiceCreate(ServiceBase):
    pass


class Service(ServiceBase):
    id: uuid.UUID

    class Config:
        orm_mode = True


class ServiceUpdate(BaseModel):
    category: Optional[str]
    color: Optional[str]
    owner: Optional[str]

    _validate_color = validator("color", allow_reuse=True)(validate_color)


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


class AndroidData(BaseModel):
    title: str
    body: str
    url: str


class AndroidMessage(BaseModel):
    token: str
    data: AndroidData


class AndroidPayload(BaseModel):
    message: AndroidMessage


class Aps(BaseModel):
    alert: Alert
    badge: int
    sound: str = "default"


class ApnPayload(BaseModel):
    aps: Aps
