import uuid
from sqlalchemy.orm import Session
from app import schemas


def test_user(db: Session, user_factory) -> None:
    username = "johndoe"
    user = user_factory(username=username)
    assert user.username == username
    assert user.is_active
    assert not user.is_admin
    assert not hasattr(user, "token")
    assert user.device_tokens == []
    assert user._device_tokens == ""


def test_user_add_device_token(db: Session, user) -> None:
    device_token1 = "my-token"
    user.add_device_token(device_token1)
    assert user.device_tokens == [device_token1]
    assert user._device_tokens == device_token1
    device_token2 = "another-token"
    user.add_device_token(device_token2)
    assert user.device_tokens == [device_token1, device_token2]
    assert user._device_tokens == f"{device_token1};{device_token2}"
    # Adding an existing token doesn't change anything
    user.add_device_token(device_token1)
    assert user.device_tokens == [device_token1, device_token2]


def test_user_remove_device_token(db: Session, user_factory) -> None:
    user = user_factory(device_tokens=["first-token", "second-token"])
    # Removing a non existing token doesn't change anything
    user.remove_device_token("foo")
    assert user.device_tokens == ["first-token", "second-token"]
    user.remove_device_token("first-token")
    assert user.device_tokens == ["second-token"]


def test_user_subscribe_service(db: Session, user, service_factory):
    service1 = service_factory()
    service2 = service_factory()
    assert user.services == []
    assert service1.subscribers == []
    assert service2.subscribers == []
    user.subscribe(service1)
    assert user.services == [service1]
    assert service1.subscribers == [user]
    assert service2.subscribers == []
    user.subscribe(service2)
    assert user.services == [service1, service2]
    assert service1.subscribers == [user]
    assert service2.subscribers == [user]
    # Subscribing to the same service doesn't change anything
    user.subscribe(service2)
    assert user.services == [service1, service2]
    assert service1.subscribers == [user]
    assert service2.subscribers == [user]


def test_user_unsubscribe_service(db: Session, user, service_factory):
    service1 = service_factory()
    service2 = service_factory()
    user.services.append(service1)
    user.services.append(service2)
    assert service1.subscribers == [user]
    assert service2.subscribers == [user]
    user.unsubscribe(service1)
    assert user.services == [service2]
    assert service1.subscribers == []
    assert service2.subscribers == [user]
    # Unsubscribing from the same service doesn't change anything
    user.unsubscribe(service1)
    assert user.services == [service2]
    assert service1.subscribers == []
    assert service2.subscribers == [user]
    user.unsubscribe(service2)
    assert user.services == []
    assert service1.subscribers == []
    assert service2.subscribers == []


def test_service(db, service_factory):
    category = "My service"
    service = service_factory(category=category)
    assert service.category == category
    assert isinstance(service.id, uuid.UUID)
    assert service.subscribers == []
    assert service.notifications == []


def test_service_to_user_service(db, user_factory, service):
    user1 = user_factory()
    user2 = user_factory()
    user1.subscribe(service)
    assert service.subscribers == [user1]
    user1_service = service.to_user_service(user1)
    user2_service = service.to_user_service(user2)
    assert user1_service == schemas.UserService(
        id=service.id,
        category=service.category,
        color=service.color,
        owner=service.owner,
        is_subscribed=True,
    )
    assert user2_service == schemas.UserService(
        id=service.id,
        category=service.category,
        color=service.color,
        owner=service.owner,
        is_subscribed=False,
    )


def test_service_notifications(db, service, notification_factory):
    notification1 = notification_factory(service=service)
    notification2 = notification_factory(service=service)
    assert service.notifications == [notification1, notification2]


def test_user_notifications(db, user, service, notification_factory):
    # User is subscribed to service
    user.subscribe(service)
    assert user.services == [service]
    notification1 = notification_factory(service=service)
    # The notification is added to the service but NOT to the subscribed user by default
    assert service.notifications == [notification1]
    assert user.notifications == []
    assert notification1.users_notification == []
    # Notification needs to be explicitely added to the user
    user.notifications.append(notification1)
    assert user.notifications == [notification1]
    assert notification1.users_notification == [user.user_notifications[0]]


def test_user_notifications_read(db, user_factory, notification):
    user1 = user_factory()
    user2 = user_factory()
    user1.notifications.append(notification)
    user2.notifications.append(notification)
    # Set user1 notification to read
    user1_notification = user1.user_notifications[0]
    user2_notification = user2.user_notifications[0]
    user1_notification.is_read = True
    assert user1_notification.is_read
    assert not user2_notification.is_read
    assert user1_notification.notification == notification
    assert user2_notification.notification == notification
    assert notification.users_notification == [user1_notification, user2_notification]


def test_notification_to_user_notification(db, user, notification_factory):
    notification1 = notification_factory()
    notification2 = notification_factory()
    user.notifications.append(notification1)
    user.notifications.append(notification2)
    db_user_notification1 = user.user_notifications[0]
    db_user_notification1.is_read = True
    db_user_notification2 = user.user_notifications[1]
    db.commit()
    assert user.notifications == [notification1, notification2]
    assert user.user_notifications == [db_user_notification1, db_user_notification2]
    user_notification1 = db_user_notification1.to_user_notification()
    user_notification2 = db_user_notification2.to_user_notification()
    assert user_notification1 == schemas.UserNotification(
        id=notification1.id,
        timestamp=notification1.timestamp,
        title=notification1.title,
        subtitle=notification1.subtitle,
        url=notification1.url,
        service_id=notification1.service.id,
        is_read=True,
    )
    assert user_notification2 == schemas.UserNotification(
        id=notification2.id,
        timestamp=notification2.timestamp,
        title=notification2.title,
        subtitle=notification2.subtitle,
        url=notification2.url,
        service_id=notification2.service.id,
        is_read=False,
    )
