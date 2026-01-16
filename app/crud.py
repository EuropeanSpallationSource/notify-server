import datetime
import uuid
from fastapi.logger import logger
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas
from .settings import ADMIN_USERS, DEMO_ACCOUNT_SERVICE


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
    logger.info(
        f"New user created: {schemas.User.model_validate(db_user).model_dump_json()}"
    )
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
    for key, value in updated_info.model_dump().items():
        if value is not None:
            logger.info(f"Update {key} to {value} for user {user.username}")
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def update_user_login_token_expire_date(
    db: Session, user: models.User, expire_date: datetime.datetime
) -> models.User:
    logger.info(
        f"Update login_token_expire_date to {expire_date} for user {user.username}"
    )
    user.login_token_expire_date = expire_date
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


def get_services(db: Session, demo: bool = False):
    """Return all services sorted by category"""
    if demo:
        return (
            db.query(models.Service)
            .filter(models.Service.category == DEMO_ACCOUNT_SERVICE)
            .all()
        )
    else:
        return db.query(models.Service).order_by(models.Service.category).all()


def create_service(db: Session, service: schemas.ServiceCreate):
    db_service = models.Service(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    logger.info(
        f"New service created: {schemas.Service.model_validate(db_service).model_dump_json()}"
    )
    return db_service


def update_service(
    db: Session, service: models.Service, updated_info: schemas.ServiceUpdate
) -> models.Service:
    for key, value in updated_info.model_dump().items():
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
    if user.username == "demo":
        services = get_services(db, demo=True)
    else:
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
    db_notification = models.Notification(**notification.model_dump(), service=service)
    db.add(db_notification)
    for user in service.subscribers:
        user.notifications.append(db_notification)
    db.commit()
    db.refresh(db_notification)
    logger.info(
        f"New notification created for '{service.category}': {schemas.Notification.model_validate(db_notification).model_dump_json()}"
    )
    return db_notification


def get_notification(
    db: Session, notification_id: int
) -> Optional[models.Notification]:
    return (
        db.query(models.Notification)
        .filter(models.Notification.id == notification_id)
        .first()
    )


def get_user_notifications(
    db: Session,
    user: models.User,
    limit: int = 0,
    filter_services_id: Optional[List[uuid.UUID]] = None,
    sort: schemas.SortOrder = schemas.SortOrder.desc,
) -> List[schemas.UserNotification]:
    """Return the latest user's notifications sorted by timestamp

    If limit is 0, all notifications are returned
    Otherwise, only the number requested
    If a list of services id is given, only notifcations part of those are returned.
    The newest notifications are always returned. Sorting by ascending order
    will just reverse that list.
    
    Notifications are filtered based on user's service exclude_keywords settings.
    """
    query = (
        db.query(models.UserNotification)
        .filter(
            models.UserNotification.user_id == user.id,
        )
        .join(models.Notification)
        .outerjoin(
            models.UserServiceFilter,
            and_(
                models.UserServiceFilter.user_id == user.id,
                models.UserServiceFilter.service_id == models.Notification.service_id
            )
        )
    )
    if filter_services_id is not None:
        query = query.filter(models.Notification.service_id.in_(filter_services_id))
    
    query = query.order_by(desc(models.Notification.timestamp))
    query = query.limit(limit) if limit > 0 else query.all()
    
    # Convert to user notifications
    user_notifications = []
    for un in query:
        notification_dict = un.to_user_notification()
        
        # Apply include/exclude keywords filter
        # Get the UserServiceFilter for this notification's service
        user_filter = db.query(models.UserServiceFilter).filter(
            models.UserServiceFilter.user_id == user.id,
            models.UserServiceFilter.service_id == un.notification.service_id
        ).first()
        
        # Check if notification should be included
        should_include = True
        
        if user_filter:
            notification_title = notification_dict.title.lower()
            notification_subtitle = notification_dict.subtitle.lower() if notification_dict.subtitle else ''
            notification_url = notification_dict.url.lower() if notification_dict.url else ''
            
            # Check exclude_keywords first (takes priority)
            if user_filter.exclude_keywords:
                exclude_list = [kw.strip().lower() for kw in user_filter.exclude_keywords.split(';') if kw.strip()]
                for keyword in exclude_list:
                    if keyword in notification_title or keyword in notification_subtitle or keyword in notification_url:
                        should_include = False
                        break
            
            # If not excluded, check include_keywords (if set, must match at least one)
            if should_include and user_filter.include_keywords:
                include_list = [kw.strip().lower() for kw in user_filter.include_keywords.split(';') if kw.strip()]
                has_match = False
                for keyword in include_list:
                    if keyword in notification_title or keyword in notification_subtitle or keyword in notification_url:
                        has_match = True
                        break
                should_include = has_match
        
        if should_include:
            user_notifications.append(notification_dict)
    
    # Sorting in ascending order is mostly for backward compatibility
    if sort == schemas.SortOrder.asc:
        user_notifications.reverse()
    
    return user_notifications


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
    date_limit = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=keep_days
    )
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


def get_user_service_filter(
    db: Session, user_id: int, service_id: uuid.UUID
) -> Optional[models.UserServiceFilter]:
    """Get filter configuration for a user's service subscription"""
    return (
        db.query(models.UserServiceFilter)
        .filter(
            models.UserServiceFilter.user_id == user_id,
            models.UserServiceFilter.service_id == service_id,
        )
        .first()
    )


def create_or_update_user_service_filter(
    db: Session,
    user: models.User,
    service_id: uuid.UUID,
    filter_update: schemas.UserServiceFilterUpdate,
) -> models.UserServiceFilter:
    """Create or update filter settings for a user's service subscription"""
    filter_record = get_user_service_filter(db, user.id, service_id)

    if filter_record is None:
        # Create new filter
        filter_record = models.UserServiceFilter(
            user_id=user.id,
            service_id=service_id,
            include_keywords=filter_update.include_keywords or "",
            exclude_keywords=filter_update.exclude_keywords or "",
        )
        db.add(filter_record)
    else:
        # Update existing filter
        if filter_update.include_keywords is not None:
            filter_record.include_keywords = filter_update.include_keywords
        if filter_update.exclude_keywords is not None:
            filter_record.exclude_keywords = filter_update.exclude_keywords

    db.commit()
    db.refresh(filter_record)
    logger.info(
        f"Filter updated for user {user.username} on service {service_id}: "
        f"include={filter_record.include_keywords}, exclude={filter_record.exclude_keywords}"
    )
    return filter_record


def delete_user_service_filter(
    db: Session, user_id: int, service_id: uuid.UUID
) -> None:
    """Delete filter for a user's service subscription"""
    filter_record = get_user_service_filter(db, user_id, service_id)
    if filter_record:
        db.delete(filter_record)
        db.commit()
        logger.info(f"Filter deleted for user {user_id} on service {service_id}")
