from __future__ import annotations
import datetime
import re
import uuid
from enum import Enum
from typing import List, Optional
from typing_extensions import Annotated
from pydantic import ConfigDict, BaseModel
from pydantic.functional_validators import AfterValidator

RE_COLOR = re.compile(r"^[0-9a-fA-F]{6}$")


def validate_color(color: str) -> str:
    if RE_COLOR.match(color) is None:
        raise ValueError("Color should match [0-9a-fA-F]{6}")
    return color


Color = Annotated[str, AfterValidator(validate_color)]


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
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class ServiceBase(BaseModel):
    category: str
    color: Color
    owner: str


class ServiceCreate(ServiceBase):
    pass


class Service(ServiceBase):
    id: uuid.UUID
    model_config = ConfigDict(from_attributes=True)


class ServiceUpdate(BaseModel):
    category: Optional[str] = None
    color: Optional[Color] = None
    owner: Optional[str] = None


class UserService(Service):
    is_subscribed: bool


class UserUpdateService(BaseModel):
    id: uuid.UUID
    is_subscribed: bool


class UserServiceForm(UserService):
    is_selected: bool

    @classmethod
    def from_user_service(cls, user_service: UserService):
        return cls(**user_service.model_dump(), is_selected=user_service.is_subscribed)


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
    model_config = ConfigDict(from_attributes=True)


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
