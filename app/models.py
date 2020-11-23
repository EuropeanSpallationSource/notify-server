from __future__ import annotations
import uuid
from typing import List
from sqlalchemy import Table, Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship, backref
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
    _apn_tokens = Column(String, default="")
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

    def unread_notifications(self) -> List[schemas.UserNotification]:
        return [
            user_notification.to_user_notification()
            for user_notification in self.user_notifications
            if not user_notification.is_read
        ]

    @property
    def nb_unread_notifications(self) -> int:
        return len(self.unread_notifications())

    @property
    def apn_tokens(self):
        if not self._apn_tokens:
            return []
        return [token for token in self._apn_tokens.split(";")]

    @apn_tokens.setter
    def apn_tokens(self, value: List[str]):
        self._apn_tokens = ";".join(value)

    def add_apn_token(self, value: str):
        if value in self.apn_tokens:
            return
        if not self._apn_tokens:
            self._apn_tokens = value
        else:
            self._apn_tokens += f";{value}"

    def remove_apn_token(self, value: str):
        if value in self.apn_tokens:
            self.apn_tokens = [token for token in self.apn_tokens if token != value]

    def subscribe(self, service: Service) -> None:
        if service not in self.services:
            self.services.append(service)

    def unsubscribe(self, service: Service) -> None:
        if service in self.services:
            self.services.remove(service)


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

    def to_alert(self) -> schemas.Alert:
        return schemas.Alert(title=self.title, subtitle=self.subtitle)


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
