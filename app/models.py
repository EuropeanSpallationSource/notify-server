from __future__ import annotations
import uuid
from typing import List
from sqlalchemy import (
    Table,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship, backref, Session
from datetime import datetime
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.associationproxy import association_proxy
from .database import Base
from . import schemas


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    From https://docs.sqlalchemy.org/en/14/core/custom_types.html#backend-agnostic-guid-type
    """

    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


# Table for the many-to-many relationships between users and services
users_services_table = Table(
    "users_services",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("service_id", GUID, ForeignKey("services.id")),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    # Store list of APN tokens as semi-colon separated string
    _device_tokens = Column(String, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    services = relationship(
        "Service",
        secondary=users_services_table,
        back_populates="subscribers",
        order_by="Service.category",
    )
    # association proxy of "user_notifications" collection
    # to "notification" attribute
    notifications = association_proxy(
        "user_notifications",
        "notification",
    )

    @property
    def nb_unread_notifications(self) -> int:
        session = Session.object_session(self)
        query = session.query(UserNotification).filter(
            UserNotification.user_id == self.id,
            UserNotification.is_read.is_(False),
        )
        return query.with_entities(func.count()).scalar()

    @property
    def device_tokens(self):
        if not self._device_tokens:
            return []
        return [token for token in self._device_tokens.split(";")]

    @device_tokens.setter
    def device_tokens(self, value: List[str]):
        self._device_tokens = ";".join(value)

    @property
    def ios_tokens(self):
        return [token for token in self.device_tokens if len(token) == 64]

    @property
    def android_tokens(self):
        return [token for token in self.device_tokens if len(token) > 64]

    def add_device_token(self, value: str):
        if value in self.device_tokens:
            return
        if not self._device_tokens:
            self._device_tokens = value
        else:
            self._device_tokens += f";{value}"

    def remove_device_token(self, value: str):
        if value in self.device_tokens:
            self.device_tokens = [
                token for token in self.device_tokens if token != value
            ]

    def subscribe(self, service: Service) -> None:
        if service not in self.services:
            self.services.append(service)

    def unsubscribe(self, service: Service) -> None:
        if service in self.services:
            self.services.remove(service)

    def to_v1(self):
        return schemas.UserV1(
            id=self.id,
            username=self.username,
            apn_tokens=self.device_tokens,
            is_active=self.is_active,
            is_admin=self.is_admin,
        )


class Service(Base):
    __tablename__ = "services"

    id = Column(GUID, default=uuid.uuid4, primary_key=True, index=True)
    category = Column(String, index=True, nullable=False)
    color = Column(String)
    owner = Column(String)

    notifications = relationship(
        "Notification", backref="service", order_by="Notification.timestamp"
    )
    subscribers = relationship(
        "User", secondary=users_services_table, back_populates="services"
    )

    def to_user_service(self, user: User) -> schemas.UserService:
        is_subscribed = user in self.subscribers
        return schemas.UserService(
            **schemas.Service.from_orm(self).dict(), is_subscribed=is_subscribed
        )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow, nullable=False)
    title = Column(String, nullable=False)
    subtitle = Column(String)
    url = Column(String)
    service_id = Column(GUID, ForeignKey("services.id"), nullable=False)

    # The maximum payload size is 4096 bytes for Apple notification
    # https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CreatingtheNotificationPayload.html#//apple_ref/doc/uid/TP40008194-CH10-SW1
    # There is no need to send very long messages. Only a small part is displayed as push notification.
    # When opened, the full message is retrieved from the notify server API.
    # -> Limit subtitle to 256 characters maximum
    def to_alert(self) -> schemas.Alert:
        return schemas.Alert(title=self.title, subtitle=self.subtitle[:256])

    def to_android_data(self) -> schemas.AndroidData:
        return schemas.AndroidData(
            title=self.title, body=self.subtitle[:256], url=self.url
        )


class UserNotification(Base):
    __tablename__ = "users_notifications"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), primary_key=True)
    is_read = Column(Boolean, default=False)

    # bidirectional attribute/collection of "user"/"user_notifications"
    user = relationship(
        User, backref=backref("user_notifications", cascade="all, delete-orphan")
    )
    # reference to the "Notification" object
    notification = relationship("Notification", backref="users_notification")

    def __init__(self, notification=None, user=None, is_read=False):
        # Note that notification must be the first argument of the __init__ method
        # because that's how it's passed by the association proxy
        self.user = user
        self.notification = notification
        self.is_read = is_read

    def to_user_notification(self) -> schemas.UserNotification:
        return schemas.UserNotification(
            **schemas.Notification.from_orm(self.notification).dict(),
            is_read=self.is_read,
        )

    def to_apn_payload(self) -> schemas.ApnPayload:
        aps = schemas.Aps(
            alert=self.notification.to_alert(), badge=self.user.nb_unread_notifications
        )
        return schemas.ApnPayload(aps=aps)

    def to_android_payload(self, token) -> schemas.AndroidPayload:
        message = schemas.AndroidMessage(
            token=token,
            data=self.notification.to_android_data(),
        )
        return schemas.AndroidPayload(message=message)
