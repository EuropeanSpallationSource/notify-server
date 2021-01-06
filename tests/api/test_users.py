import pytest
from fastapi.testclient import TestClient
from app import schemas, models, utils


def user_authorization_headers(username):
    token = utils.create_access_token(username)
    return {"Authorization": f"Bearer {token}"}


def test_read_current_user_profile(client: TestClient, user):
    response = client.get(
        "/api/v1/users/user/profile", headers=user_authorization_headers(user.username)
    )
    assert response.status_code == 200
    assert response.json() == schemas.User.from_orm(user).dict()


def test_read_current_user_profile_no_authorization_header(client: TestClient):
    response = client.get("/api/v1/users/user/profile")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_read_current_user_profile_invalid_token(client: TestClient):
    response = client.get(
        "/api/v1/users/user/profile", headers={"Authorization": "Bearer xxxxxxx"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_read_current_user_profile_invalid_username(client: TestClient):
    response = client.get(
        "/api/v1/users/user/profile", headers=user_authorization_headers("foo")
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Unknown user foo"}


def test_read_current_user_profile_expired_token(client: TestClient, user):
    token = utils.create_access_token(user.username, expires_delta_minutes=-5)
    response = client.get(
        "/api/v1/users/user/profile", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Token has expired"}


def test_read_current_user_profile_inactive(client: TestClient, user_factory):
    user = user_factory(is_active=False)
    response = client.get(
        "/api/v1/users/user/profile", headers=user_authorization_headers(user.username)
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "Inactive user"}


def test_create_current_user_apn_token_no_token(client: TestClient, db, user):
    assert user.apn_tokens == []
    apn_token = "my-token"
    response = client.post(
        "/api/v1/users/user/apn-token",
        headers=user_authorization_headers(user.username),
        json={"apn_token": apn_token},
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "apn_tokens": [apn_token],
        "is_active": True,
        "is_admin": False,
    }


def test_create_current_user_apn_token_new_token(client: TestClient, user_factory):
    user = user_factory(apn_tokens=["first-token"])
    assert user.apn_tokens == ["first-token"]
    apn_token = "second-token"
    response = client.post(
        "/api/v1/users/user/apn-token",
        headers=user_authorization_headers(user.username),
        json={"apn_token": apn_token},
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "apn_tokens": ["first-token", apn_token],
        "is_active": True,
        "is_admin": False,
    }


def test_create_current_user_apn_token_existing_token(client: TestClient, user_factory):
    apn_token = "my-token"
    user = user_factory(apn_tokens=[apn_token])
    response = client.post(
        "/api/v1/users/user/apn-token",
        headers=user_authorization_headers(user.username),
        json={"apn_token": apn_token},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": user.username,
        "apn_tokens": [apn_token],
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
    assert db_user.notifications == [notification3, notification1]
    assert db_user.nb_unread_notifications == 1
    assert db_user.user_notifications[0].is_read
    assert not db_user.user_notifications[1].is_read


def test_read_users(client: TestClient, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    user3 = user_factory()
    admin = user_factory(is_admin=True)
    response = client.get(
        "/api/v1/users/", headers=user_authorization_headers(admin.username)
    )
    assert response.status_code == 200
    users = [
        {
            "id": user.id,
            "username": user.username,
            "apn_tokens": user.apn_tokens,
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
        f"/api/v1/users/{user1.id}",
        headers=user_authorization_headers(admin.username),
        json=updated_info,
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": user1.id,
        "username": user1.username,
        "apn_tokens": user1.apn_tokens,
        "is_admin": expected_admin,
        "is_active": expected_active,
    }


def test_update_user_invalid_id(client: TestClient, admin_token_headers):
    response = client.patch(
        "/api/v1/users/1234",
        headers=admin_token_headers,
        json={},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
