import pytest
from fastapi.testclient import TestClient
from app import schemas, models, utils


def user_authorization_headers(username):
    token = utils.create_access_token(username)
    return {"Authorization": f"Bearer {token}"}


def test_read_current_user_profile_v1(client: TestClient, user):
    response = client.get(
        "/api/v1/users/user/profile", headers=user_authorization_headers(user.username)
    )
    assert response.status_code == 200
    assert response.json() == user.to_v1().dict()


def test_read_current_user_profile(client: TestClient, user):
    response = client.get(
        "/api/v2/users/user/profile", headers=user_authorization_headers(user.username)
    )
    assert response.status_code == 200
    assert response.json() == schemas.User.from_orm(user).dict()


@pytest.mark.parametrize("api_version", ["v1", "v2"])
def test_read_current_user_profile_no_authorization_header(
    client: TestClient, api_version
):
    response = client.get(f"/api/{api_version}/users/user/profile")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("api_version", ["v1", "v2"])
def test_read_current_user_profile_invalid_token(client: TestClient, api_version):
    response = client.get(
        f"/api/{api_version}/users/user/profile",
        headers={"Authorization": "Bearer xxxxxxx"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


@pytest.mark.parametrize("api_version", ["v1", "v2"])
def test_read_current_user_profile_invalid_username(client: TestClient, api_version):
    response = client.get(
        f"/api/{api_version}/users/user/profile",
        headers=user_authorization_headers("foo"),
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Unknown user foo"}


@pytest.mark.parametrize("api_version", ["v1", "v2"])
def test_read_current_user_profile_expired_token(client: TestClient, user, api_version):
    token = utils.create_access_token(user.username, expires_delta_minutes=-5)
    response = client.get(
        f"/api/{api_version}/users/user/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Token has expired"}


@pytest.mark.parametrize("api_version", ["v1", "v2"])
def test_read_current_user_profile_inactive(
    client: TestClient, user_factory, api_version
):
    user = user_factory(is_active=False)
    response = client.get(
        f"/api/{api_version}/users/user/profile",
        headers=user_authorization_headers(user.username),
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


def test_create_current_user_apn_token_v2_not_found(client: TestClient, db, user):
    response = client.post(
        "/api/v2/users/user/apn-token",
        headers=user_authorization_headers(user.username),
        json={"apn-token": "foo"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "endpoint, token_name",
    [
        ("/api/v1/users/user/apn-token", "apn_token"),
        ("/api/v2/users/user/device-token", "device_token"),
    ],
)
def test_create_current_user_device_token_no_token(
    client: TestClient, db, user, endpoint, token_name
):
    assert user.device_tokens == []
    device_token = "my-token"
    response = client.post(
        endpoint,
        headers=user_authorization_headers(user.username),
        json={token_name: device_token},
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        f"{token_name}s": [device_token],
        "is_active": True,
        "is_admin": False,
    }


@pytest.mark.parametrize(
    "endpoint, token_name",
    [
        ("/api/v1/users/user/apn-token", "apn_token"),
        ("/api/v2/users/user/device-token", "device_token"),
    ],
)
def test_create_current_user_device_token_new_token(
    client: TestClient, user_factory, endpoint, token_name
):
    user = user_factory(device_tokens=["first-token"])
    assert user.device_tokens == ["first-token"]
    device_token = "second-token"
    response = client.post(
        endpoint,
        headers=user_authorization_headers(user.username),
        json={token_name: device_token},
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        f"{token_name}s": ["first-token", device_token],
        "is_active": True,
        "is_admin": False,
    }


@pytest.mark.parametrize(
    "endpoint, token_name",
    [
        ("/api/v1/users/user/apn-token", "apn_token"),
        ("/api/v2/users/user/device-token", "device_token"),
    ],
)
def test_create_current_user_device_token_existing_token(
    client: TestClient, user_factory, endpoint, token_name
):
    device_token = "my-token"
    user = user_factory(device_tokens=[device_token])
    response = client.post(
        endpoint,
        headers=user_authorization_headers(user.username),
        json={token_name: device_token},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        f"{token_name}s": [device_token],
        "is_active": True,
        "is_admin": False,
    }


def test_read_current_user_services(client: TestClient, db, user, service_factory):
    # Create some services and subscribe to one
    service1 = service_factory()
    service2 = service_factory()
    user.subscribe(service1)
    db.commit()
    response = client.get(
        "/api/v1/users/user/services", headers=user_authorization_headers(user.username)
    )
    assert response.status_code == 200
    assert response.json() == sorted(
        [
            {
                "id": str(service1.id),
                "category": service1.category,
                "color": service1.color,
                "owner": service1.owner,
                "is_subscribed": True,
            },
            {
                "id": str(service2.id),
                "category": service2.category,
                "color": service2.color,
                "owner": service2.owner,
                "is_subscribed": False,
            },
        ],
        key=lambda s: s["category"],
    )


def test_update_current_user_services(client: TestClient, db, user, service_factory):
    # Create some services and subscribe to one
    service1 = service_factory()
    service2 = service_factory()
    service3 = service_factory()
    user.subscribe(service1)
    user.subscribe(service2)
    db.commit()
    assert user.services == sorted([service1, service2], key=lambda s: s.category)
    response = client.patch(
        "/api/v1/users/user/services",
        headers=user_authorization_headers(user.username),
        json=[
            {"id": str(service1.id), "is_subscribed": True},
            {"id": str(service2.id), "is_subscribed": False},
            {"id": str(service3.id), "is_subscribed": True},
        ],
    )
    assert response.status_code == 204
    db_user = db.query(models.User).get(user.id)
    assert db_user.services == sorted([service1, service3], key=lambda s: s.category)


def test_read_current_user_notifications(
    client: TestClient, db, user, notification_factory
):
    notification1 = notification_factory()
    notification2 = notification_factory()
    # extra notification to check that only users notifications are returned
    notification_factory()
    user.notifications.append(notification1)
    user.notifications.append(notification2)
    db.commit()
    response = client.get(
        "/api/v1/users/user/notifications",
        headers=user_authorization_headers(user.username),
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": notification1.id,
            "is_read": False,
            "service_id": str(notification1.service_id),
            "subtitle": notification1.subtitle,
            "timestamp": notification1.timestamp.isoformat(),
            "title": notification1.title,
            "url": notification1.url,
        },
        {
            "id": notification2.id,
            "is_read": False,
            "service_id": str(notification2.service_id),
            "subtitle": notification2.subtitle,
            "timestamp": notification2.timestamp.isoformat(),
            "title": notification2.title,
            "url": notification2.url,
        },
    ]


def test_update_current_user_notifications(
    client: TestClient, db, user, notification_factory
):
    notification1 = notification_factory()
    notification2 = notification_factory()
    notification3 = notification_factory()
    user.notifications.append(notification1)
    user.notifications.append(notification2)
    user.notifications.append(notification3)
    assert user.nb_unread_notifications == 3
    db.commit()
    response = client.patch(
        "/api/v1/users/user/notifications",
        headers=user_authorization_headers(user.username),
        json=[
            {"id": notification1.id, "status": "read"},
            {"id": notification2.id, "status": "deleted"},
            {"id": notification3.id, "status": "unread"},
        ],
    )
    assert response.status_code == 204
    db_user = db.query(models.User).get(user.id)
    assert db_user.notifications == [notification1, notification3]
    assert db_user.nb_unread_notifications == 1
    assert db_user.user_notifications[0].is_read
    assert not db_user.user_notifications[1].is_read


def test_read_users(client: TestClient, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    user3 = user_factory()
    admin = user_factory(is_admin=True)
    response = client.get(
        "/api/v2/users/", headers=user_authorization_headers(admin.username)
    )
    assert response.status_code == 200
    users = [
        {
            "id": user.id,
            "username": user.username,
            "device_tokens": user.device_tokens,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
        }
        for user in (user1, user2, user3, admin)
    ]
    assert response.json() == sorted(users, key=lambda u: u["username"])


@pytest.mark.parametrize(
    "updated_info,expected_active,expected_admin",
    [
        ({}, True, False),
        ({"is_admin": True}, True, True),
        ({"is_active": False}, False, False),
    ],
)
def test_update_user(
    client: TestClient,
    user_factory,
    updated_info,
    expected_active,
    expected_admin,
):
    user1 = user_factory()
    admin = user_factory(is_admin=True)
    assert not user1.is_admin
    response = client.patch(
        f"/api/v2/users/{user1.id}",
        headers=user_authorization_headers(admin.username),
        json=updated_info,
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": user1.id,
        "username": user1.username,
        "device_tokens": user1.device_tokens,
        "is_admin": expected_admin,
        "is_active": expected_active,
    }


def test_update_user_invalid_id(client: TestClient, admin_token_headers):
    response = client.patch(
        "/api/v2/users/1234",
        headers=admin_token_headers,
        json={},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
