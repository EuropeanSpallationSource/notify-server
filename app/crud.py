import datetime
import uuid
from fastapi.logger import logger
from sqlalchemy import desc
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


def get_services(db: Session, demo: bool=False):
    """Return all services sorted by category"""
    if demo:
        return db.query(models.Service).filter(models.Service.category == "test").all()
    else:
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


def delete_service(db: Session, service: models.Service) -> None:
    # First retrieve all notifications id to delete
    service_notification_ids = db.query(models.Notification.id).filter(
        models.Notification.service_id == service.id
    )
    # Delete the UserNotification linked to those notifications
    db.query(models.UserNotification).filter(
        models.UserNotification.notification_id.in_(service_notification_ids.subquery())
    ).delete(synchronize_session=False)
    # Delete the notifications themselves
    service_notification_ids.delete(synchronize_session=False)
    db.delete(service)
    db.commit()


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


def get_user_notifications(
    db: Session,
    user: models.User,
    limit: int = 0,
    sort: schemas.SortOrder = schemas.SortOrder.desc,
) -> List[schemas.UserNotification]:
    """Return the latest user's notifications sorted by timestamp

    If limit is 0, all notifications are returned
    Otherwise, only the number requested
    The newest notifications are always returned. Sorting by ascending order
    will just reverse that list.
    """
    query = (
        db.query(models.UserNotification)
        .filter(
            models.UserNotification.user_id == user.id,
        )
        .join(models.Notification)
        .order_by(desc(models.Notification.timestamp))
    )
    if limit > 0:
        query = query.limit(limit)
    else:
        query = query.all()
    notifications = [un.to_user_notification() for un in query]
    # Sorting in ascending order is mostly for backward compatibility
    if sort == schemas.SortOrder.asc:
        notifications.reverse()
    return notifications


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


def delete_notifications(db: Session, keep_days: int) -> None:
    """Delete notifications older than X days"""
    date_limit = datetime.datetime.utcnow() - datetime.timedelta(days=keep_days)
    # First retrieve all notifications id to delete
    old_notification_ids = db.query(models.Notification.id).filter(
        models.Notification.timestamp < date_limit
    )
    # Delete the UserNotification linked to those notifications
    db.query(models.UserNotification).filter(
        models.UserNotification.notification_id.in_(old_notification_ids.subquery())
    ).delete(synchronize_session=False)
    # Delete the notifications themselves
    old_notification_ids.delete(synchronize_session=False)
    db.commit()
