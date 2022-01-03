import datetime
import pytest
import uuid
from operator import attrgetter
from app import crud, models, schemas


def test_create_user(db):
    username = "johndoe"
    user = crud.create_user(db, username=username)
    assert user.username == username
    assert user.is_active
    assert not user.is_admin


@pytest.mark.parametrize(
    "username, expected_is_admin",
    [("foo", False), ("admin1", True), ("admin2", True), ("admin3", False)],
)
def test_create_user_admin(db, username, expected_is_admin):
    # admin1 and admin2 are defined in ADMIN_USERS in conftest.py
    user = crud.create_user(db, username=username)
    assert user.is_admin is expected_is_admin


def test_get_user_by_username(db, user):
    retrieved_user = crud.get_user_by_username(db, user.username)
    assert retrieved_user == user
    retrieved_user = crud.get_user_by_username(db, "foo")
    assert retrieved_user is None


def test_create_service(db):
    service = crud.create_service(
        db, schemas.ServiceCreate(category="My Service", color="00FF00", owner="John")
    )
    assert service.category == "My Service"
    assert isinstance(service.id, uuid.UUID)
    assert service.subscribers == []
    assert service.notifications == []


def test_get_service(db, service):
    retrieved_service = crud.get_service(db, service.id)
    assert retrieved_service == service
    retrieved_service = crud.get_service(db, uuid.uuid4())
    assert retrieved_service is None


def test_delete_service(db, service_factory):
    service1 = service_factory(category="service1")
    service2 = service_factory(category="service2")
    service3 = service_factory(category="service3")
    assert db.query(models.Service).order_by(models.Service.category).all() == [
        service1,
        service2,
        service3,
    ]
    crud.delete_service(db, service2)
    assert db.query(models.Service).order_by(models.Service.category).all() == [
        service1,
        service3,
    ]


def test_delete_service_with_user(db, user, service_factory):
    service1 = service_factory(category="category1")
    service2 = service_factory(category="category2")
    service3 = service_factory(category="category3")
    user.subscribe(service1)
    user.subscribe(service3)
    db.commit()
    notification1 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message1"), service1
    )
    notification2 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message2"), service1
    )
    notification3 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message3"), service2
    )
    notification4 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message4"), service1
    )
    notification5 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message5"), service2
    )
    notification6 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message6"), service3
    )
    assert user.notifications == [
        notification1,
        notification2,
        notification4,
        notification6,
    ]
    assert db.query(models.Notification).order_by(models.Notification.title).all() == [
        notification1,
        notification2,
        notification3,
        notification4,
        notification5,
        notification6,
    ]
    crud.delete_service(db, service1)
    # Check that service1 UserNotifications have been deleted
    assert user.notifications == [notification6]
    # Check that service1 notifications have been deleted
    assert db.query(models.Notification).order_by(models.Notification.title).all() == [
        notification3,
        notification5,
        notification6,
    ]
    # Check that service1 has been deleted
    assert db.query(models.Service).order_by(models.Service.category).all() == [
        service2,
        service3,
    ]


def test_get_user_services(db, user, service_factory):
    service1 = service_factory()
    service2 = service_factory()
    service3 = service_factory()
    user.subscribe(service1)
    db.commit()
    user1_service = schemas.UserService(
        id=service1.id,
        category=service1.category,
        color=service1.color,
        owner=service1.owner,
        is_subscribed=True,
    )
    user2_service = schemas.UserService(
        id=service2.id,
        category=service2.category,
        color=service2.color,
        owner=service2.owner,
        is_subscribed=False,
    )
    user_services = crud.get_user_services(db, user)
    assert user_services == sorted(
        [user1_service, user2_service, service3.to_user_service(user)],
        key=lambda us: us.category,
    )


def test_create_service_notification(db, user_factory, service):
    title = "My message"
    subtitle = "This is a test"
    url = "https://google.com"
    user1 = user_factory()
    user2 = user_factory()
    user1.subscribe(service)
    db.commit()
    assert service.notifications == []
    assert user1.notifications == []
    assert user2.notifications == []
    notification = crud.create_service_notification(
        db,
        schemas.NotificationCreate(title=title, subtitle=subtitle, url=url),
        service=service,
    )
    assert isinstance(notification.id, int)
    assert notification.title == title
    assert notification.subtitle == subtitle
    assert notification.url == url
    # The notification was added both to the service and service subscribers
    assert service.notifications == [notification]
    assert user1.notifications == [notification]
    assert user2.notifications == []
    assert notification.users_notification == [user1.user_notifications[0]]


def test_get_user_notifications(db, user, service):
    user.subscribe(service)
    db.commit()
    notification1 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="First message"), service
    )
    notification2 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="Second message"), service
    )
    user_notifications = crud.get_user_notifications(db, user)
    user_notification1 = schemas.UserNotification(
        id=notification1.id,
        timestamp=notification1.timestamp,
        title=notification1.title,
        subtitle=notification1.subtitle,
        url=notification1.url,
        service_id=service.id,
        is_read=False,
    )
    user_notification2 = schemas.UserNotification(
        id=notification2.id,
        timestamp=notification2.timestamp,
        title=notification2.title,
        subtitle=notification2.subtitle,
        url=notification2.url,
        service_id=service.id,
        is_read=False,
    )
    assert user_notifications == [user_notification2, user_notification1]


@pytest.mark.parametrize("sort", ["asc", "desc"])
@pytest.mark.parametrize("limit", [-1, 0, 1, 10, 20, 100])
def test_get_user_notifications_limit(db, user, service, limit, sort):
    # Create some notifications
    user.subscribe(service)
    db.commit()
    notifications = []
    now = datetime.datetime.now()
    for nb in range(20):
        notification = crud.create_service_notification(
            db, schemas.NotificationCreate(title=f"message{nb}"), service
        )
        notification.timestamp = now - datetime.timedelta(minutes=nb)
        notifications.append(notification)
    # Get the user notifications
    user_notifications = crud.get_user_notifications(db, user, limit=limit, sort=sort)
    # Check the number of notifications returned
    if limit > 0 and limit <= 20:
        assert len(user_notifications) == limit
        oldest_timestamp = notifications[limit - 1].timestamp
    else:
        assert len(user_notifications) == 20
        oldest_timestamp = notifications[-1].timestamp
    # Check they are properly sorted
    # In both cases, we have the same list, but sorted in reverse order
    newest_timestamp = notifications[0].timestamp
    if sort == "asc":
        assert user_notifications[0].timestamp == oldest_timestamp
        assert user_notifications[-1].timestamp == newest_timestamp
        is_reverse = False
    elif sort == "desc":
        assert user_notifications[0].timestamp == newest_timestamp
        assert user_notifications[-1].timestamp == oldest_timestamp
        is_reverse = True
    sorted_user_notifications = sorted(
        user_notifications, key=attrgetter("timestamp"), reverse=is_reverse
    )
    assert user_notifications == sorted_user_notifications


def test_get_user_notifications_filter_services_id(db, user, service_factory):
    # Create some notifications
    service1 = service_factory()
    service2 = service_factory()
    service3 = service_factory()
    user.subscribe(service1)
    user.subscribe(service2)
    user.subscribe(service3)
    db.commit()
    notifications = []
    now = datetime.datetime.now()
    for service_nb, service in enumerate((service1, service2, service3), start=1):
        for nb in range(10):
            notification = crud.create_service_notification(
                db,
                schemas.NotificationCreate(title=f"Service{service_nb} - message{nb}"),
                service,
            )
            notification.timestamp = now - datetime.timedelta(minutes=nb + service_nb)
            notifications.append(notification)
    # Get the user notifications with filtering on the services id
    user_notifications = crud.get_user_notifications(db, user)
    assert len(user_notifications) == 30
    # Filter on service1 only
    service1_user_notifications = crud.get_user_notifications(
        db, user, filter_services_id=[service1.id]
    )
    assert len(service1_user_notifications) == 10
    for notification in service1_user_notifications:
        assert notification.title.startswith("Service1")
    # Filter on service1 and service3
    service1_3_user_notifications = crud.get_user_notifications(
        db, user, filter_services_id=[service1.id, service3.id]
    )
    assert len(service1_3_user_notifications) == 20
    for notification in service1_3_user_notifications:
        assert not notification.title.startswith("Service2")
    # Filter on all services is the same as no filtering
    services_user_notifications = crud.get_user_notifications(
        db, user, filter_services_id=[service1.id, service2.id, service3.id]
    )
    assert user_notifications == services_user_notifications
    # Filter on empty list
    assert crud.get_user_notifications(db, user, filter_services_id=[]) == []
    # Filter on unknown service id
    assert (
        crud.get_user_notifications(
            db, user, filter_services_id=["2cf81604-514a-45e1-9a34-f4368834db99"]
        )
        == []
    )


def test_update_user_services(db, user, service_factory):
    service1 = service_factory()
    service2 = service_factory()
    service3 = service_factory()
    user.subscribe(service1)
    user.subscribe(service2)
    db.commit()
    assert user.services == sorted([service1, service2], key=lambda s: s.category)
    updated_services = [
        schemas.UserUpdateService(id=service1.id, is_subscribed=False),
        schemas.UserUpdateService(id=service2.id, is_subscribed=True),
        schemas.UserUpdateService(id=service3.id, is_subscribed=True),
    ]
    crud.update_user_services(db, updated_services, user)
    # Services are updated
    db.refresh(user)
    assert user.services == sorted([service2, service3], key=lambda s: s.category)


def test_update_user_services_unknown_id(db, user, service_factory):
    service1 = service_factory()
    service2 = service_factory()
    service3 = service_factory()
    user.subscribe(service1)
    user.subscribe(service2)
    db.commit()
    assert user.services == sorted([service1, service2], key=lambda s: s.category)
    updated_services = [
        schemas.UserUpdateService(id=uuid.uuid4(), is_subscribed=False),
        schemas.UserUpdateService(id=service2.id, is_subscribed=True),
        schemas.UserUpdateService(id=service3.id, is_subscribed=True),
    ]
    crud.update_user_services(db, updated_services, user)
    # Unknown service is ignored
    # Missing service is untouched
    db.refresh(user)
    assert user.services == sorted(
        [service1, service2, service3], key=lambda s: s.category
    )


def test_update_user_notifications(db, user, service_factory):
    service1 = service_factory()
    service2 = service_factory()
    user.subscribe(service1)
    user.subscribe(service2)
    db.commit()
    notification1 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="First message"), service1
    )
    notification2 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="Second message"), service1
    )
    notification3 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="Second message"), service2
    )
    assert user.notifications == [notification1, notification2, notification3]
    unknown_id = max(notification1.id, notification2.id, notification3.id) + 1
    updated_notifications = [
        schemas.UserUpdateNotification(id=notification1.id, status="read"),
        schemas.UserUpdateNotification(id=notification2.id, status="deleted"),
        schemas.UserUpdateNotification(id=unknown_id, status="read"),
        schemas.UserUpdateNotification(id=notification3.id, status="unread"),
    ]
    crud.update_user_notifications(db, updated_notifications, user)
    #  Notifications are updated
    # Unknown notification is ignored
    db.refresh(user)
    assert user.notifications == [notification1, notification3]
    # notification2 is still in the service notifications
    # it was only deleted from the user notifications
    db_notification2 = db.query(models.Notification).get(notification2.id)
    assert db_notification2 == notification2
    assert db_notification2 in notification2.service.notifications


@pytest.mark.parametrize(
    "initial_tokens, removed, expected",
    [
        ([], "foo", []),
        (["one"], "foo", ["one"]),
        (["one"], "one", []),
        (["one", "two"], "one", ["two"]),
    ],
)
def test_remove_user_device_token(db, user_factory, initial_tokens, removed, expected):
    user = user_factory(device_tokens=initial_tokens)
    assert user.device_tokens == initial_tokens
    crud.remove_user_device_token(db, user, removed)
    assert user.device_tokens == expected


def test_delete_notifications(db, notification_factory, notification_date):
    notification1 = notification_factory(timestamp=notification_date(60))
    notification2 = notification_factory(timestamp=notification_date(40))
    notification3 = notification_factory(timestamp=notification_date(20))
    notification4 = notification_factory(timestamp=notification_date(1))
    notification5 = notification_factory()
    assert db.query(models.Notification).order_by(
        models.Notification.timestamp
    ).all() == [
        notification1,
        notification2,
        notification3,
        notification4,
        notification5,
    ]
    crud.delete_notifications(db, 30)
    assert db.query(models.Notification).order_by(
        models.Notification.timestamp
    ).all() == [
        notification3,
        notification4,
        notification5,
    ]


def test_delete_notifications_with_user(db, user, service_factory, notification_date):
    service1 = service_factory()
    service2 = service_factory()
    user.subscribe(service1)
    db.commit()
    notification1 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message1"), service1
    )
    notification1.timestamp = notification_date(40)
    notification2 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message2"), service1
    )
    notification2.timestamp = notification_date(40)
    notification3 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message3"), service2
    )
    notification3.timestamp = notification_date(35)
    notification4 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message4"), service1
    )
    notification4.timestamp = notification_date(1)
    notification5 = crud.create_service_notification(
        db, schemas.NotificationCreate(title="message5"), service2
    )
    assert user.notifications == [notification1, notification2, notification4]
    assert db.query(models.Notification).order_by(
        models.Notification.timestamp
    ).all() == [
        notification1,
        notification2,
        notification3,
        notification4,
        notification5,
    ]
    crud.delete_notifications(db, 30)
    # Check that old notifications have been deleted
    assert db.query(models.Notification).order_by(
        models.Notification.timestamp
    ).all() == [
        notification4,
        notification5,
    ]
    # Check that old UserNotifications have also been deleted
    assert user.notifications == [notification4]
