import uuid
from operator import attrgetter
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .settings import ADMIN_USERS


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_token(db: Session, token: str):
    return db.query(models.User).filter(models.User.token == token).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str):
    is_admin = username in ADMIN_USERS
    db_user = models.User(username=username, is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_apn_token(
    db: Session, apn_token: str, user: models.User
) -> models.User:
    user.add_apn_token(apn_token)
    db.commit()
    db.refresh(user)
    return user


def get_service(db: Session, service_id: uuid.UUID):
    return db.query(models.Service).filter(models.Service.id == service_id).first()


def get_services(db: Session):
    return db.query(models.Service).all()


def create_service(db: Session, service: schemas.ServiceCreate):
    db_service = models.Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service


def get_user_services(db: Session, user: models.User) -> List[schemas.UserService]:
    """Return all services for the user sorted by category"""
    services = db.query(models.Service).all()
    return sorted(
        [service.to_user_service(user) for service in services],
        key=attrgetter("category"),
    )


def update_user_services(
    db: Session, updated_services: List[schemas.UserUpdateService], user: models.User
) -> None:
    # Get all services in one query and build a dict to efficiently
    # retrieve each service by id in the loop
    services = db.query(models.Service).all()
    services_dict = {service.id: service for service in services}
    for updated_service in updated_services:
        try:
            service = services_dict[updated_service.id]
        except KeyError:
            # Skip unknown service_id
            continue
        if updated_service.is_subscribed:
            user.subscribe(service)
        else:
            user.unsubscribe(service)
    db.commit()


def create_service_notification(
    db: Session, notification: schemas.NotificationCreate, service: models.Service
):
    db_notification = models.Notification(**notification.dict(), service=service)
    db.add(db_notification)
    for user in service.subscribers:
        user.notifications.append(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_user_notifications(user: models.User) -> List[schemas.UserNotification]:
    return [un.to_user_notification() for un in user.user_notifications]


def get_user_unread_notifications(user: models.User) -> List[schemas.UserNotification]:
    return [
        user_notification
        for user_notification in get_user_notifications(user)
        if not user_notification.is_read
    ]


def get_user_nb_unread_notifications(user: models.User) -> int:
    return len(get_user_nb_unread_notifications(user))


def update_user_notifications(
    db: Session,
    updated_notifications: List[schemas.UserUpdateNotification],
    user: models.User,
) -> None:
    # Build a dict to efficiently retrieve each notification by id in the loop
    user_notifications_dict = {un.notification_id: un for un in user.user_notifications}
    for updated_notification in updated_notifications:
        try:
            user_notification = user_notifications_dict[updated_notification.id]
        except KeyError:
            # Skip unknown notification
            continue
        if updated_notification.status == schemas.NotificationStatus.read:
            user_notification.is_read = True
        elif updated_notification.status == schemas.NotificationStatus.unread:
            user_notification.is_read = False
        elif updated_notification.status == schemas.NotificationStatus.deleted:
            user.user_notifications.remove(user_notification)
    db.commit()
