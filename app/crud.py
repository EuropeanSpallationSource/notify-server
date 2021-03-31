from operator import attrgetter
import uuid
from fastapi.logger import logger
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .settings import ADMIN_USERS


def get_users(db: Session):
    """Return all users sorted by username"""
    return db.query(models.User).order_by(models.User.username).all()


def get_user(db: Session, user_id: int):
    return db.query(models.User).get(user_id)


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, username: str):
    is_admin = username in ADMIN_USERS
    db_user = models.User(username=username, is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"New user created: {schemas.User.from_orm(db_user).json()}")
    return db_user


def create_user_device_token(
    db: Session, device_token: str, user: models.User
) -> models.User:
    user.add_device_token(device_token)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session, user: models.User, updated_info: schemas.UserUpdate
) -> models.User:
    for key, value in updated_info.dict().items():
        if value is not None:
            logger.info(f"Update {key} to {value} for user {user.username}")
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()


def remove_user_device_token(
    db: Session, user: models.User, device_token: str
) -> models.User:
    user.remove_device_token(device_token)
    db.commit()
    db.refresh(user)
    return user


def get_service(db: Session, service_id: uuid.UUID):
    return db.query(models.Service).filter(models.Service.id == service_id).first()


def get_services(db: Session):
    """Return all services sorted by category"""
    return db.query(models.Service).order_by(models.Service.category).all()


def create_service(db: Session, service: schemas.ServiceCreate):
    db_service = models.Service(**service.dict())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    logger.info(f"New service created: {schemas.Service.from_orm(db_service).json()}")
    return db_service


def update_service(
    db: Session, service: models.Service, updated_info: schemas.ServiceUpdate
) -> models.Service:
    for key, value in updated_info.dict().items():
        if value is not None:
            logger.info(f"Update {key} to {value} for service {service.id}")
            setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


def get_user_services(db: Session, user: models.User) -> List[schemas.UserService]:
    """Return all services for the user sorted by category"""
    services = get_services(db)
    return [service.to_user_service(user) for service in services]


def update_user_services(
    db: Session, updated_services: List[schemas.UserUpdateService], user: models.User
) -> None:
    # Get all services in one query and build a dict to efficiently
    # retrieve each service by id in the loop
    services = get_services(db)
    services_dict = {service.id: service for service in services}
    for updated_service in updated_services:
        try:
            service = services_dict[updated_service.id]
        except KeyError:
            # Skip unknown service_id
            continue
        if updated_service.is_subscribed:
            user.subscribe(service)
            logger.info(f"User {user.username} subscribed to '{service.category}'")
        else:
            user.unsubscribe(service)
            logger.info(f"User {user.username} unsubscribed from '{service.category}'")
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
    logger.info(
        f"New notification created for '{service.category}': {schemas.Notification.from_orm(db_notification).json()}"
    )
    return db_notification


def get_user_notifications(user: models.User) -> List[schemas.UserNotification]:
    """Return all user's notifications sorted by timestamp"""
    user_notifications = [un.to_user_notification() for un in user.user_notifications]
    return sorted(user_notifications, key=attrgetter("timestamp"))[-50:]


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
