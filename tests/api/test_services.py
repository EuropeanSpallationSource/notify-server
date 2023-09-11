import json
import uuid
import pytest
from fastapi.testclient import TestClient
from app import models, schemas


@pytest.fixture(scope="module")
def sample_notification():
    return {
        "title": "My Alert",
        "subtitle": "This is a test",
        "url": "https://google.com",
    }


def db_service_to_dict(db_service: models.Service) -> dict:
    return json.loads(schemas.Service.model_validate(db_service).model_dump_json())


def test_read_services(
    client: TestClient, service_factory, user_token_headers, api_version
):
    service1 = service_factory()
    service2 = service_factory()
    response = client.get(f"/api/{api_version}/services", headers=user_token_headers)
    assert response.status_code == 200
    services = [db_service_to_dict(service1), db_service_to_dict(service2)]
    assert response.json() == sorted(services, key=lambda s: s["category"])


def test_create_service_invalid_privileges(
    client: TestClient, user_token_headers, api_version
):
    data = {"category": "My Service", "color": "FFFFFF", "owner": "foo"}
    response = client.post(
        f"/api/{api_version}/services/", headers=user_token_headers, json=data
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "The user doesn't have enough privileges"}


@pytest.mark.parametrize("color", ["blue", "#FF0000", "0000"])
def test_create_service_invalid_color(
    color, client: TestClient, admin_token_headers, api_version
):
    data = {"category": "My Service", "color": color, "owner": "foo"}
    response = client.post(
        f"/api/{api_version}/services/", headers=admin_token_headers, json=data
    )
    assert response.status_code == 422
    assert (
        response.json()["detail"][0]["msg"]
        == "Value error, Color should match [0-9a-fA-F]{6}"
    )
    assert response.json()["detail"][0]["input"] == color
    assert response.json()["detail"][0]["loc"] == ["body", "color"]
    assert response.json()["detail"][0]["type"] == "value_error"


def test_create_service(client: TestClient, db, admin_token_headers, api_version):
    data = {
        "category": "My Service",
        "color": "FF0000",
        "owner": "John",
    }
    response = client.post(
        f"/api/{api_version}/services/", headers=admin_token_headers, json=data
    )
    assert response.status_code == 201
    db_service = (
        db.query(models.Service)
        .filter(models.Service.category == data["category"])
        .first()
    )
    assert response.json() == db_service_to_dict(db_service)


@pytest.mark.parametrize("color", ["black", "00FF0000", "#00FF00"])
def test_update_service_invalid_color(
    color, client: TestClient, service_factory, admin_token_headers, api_version
):
    original_data = {
        "category": "My Service",
        "color": "FF0000",
        "owner": "John",
    }
    service = service_factory(**original_data)
    data = original_data.copy()
    data["color"] = color
    response = client.patch(
        f"/api/{api_version}/services/{service.id}",
        headers=admin_token_headers,
        json=data,
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "ctx": {"error": {}},
                "loc": ["body", "color"],
                "input": color,
                "msg": "Value error, Color should match [0-9a-fA-F]{6}",
                "type": "value_error",
                "url": "https://errors.pydantic.dev/2.1/v/value_error",
            }
        ],
    }


@pytest.mark.parametrize(
    "data", [{"category": "New service"}, {"color": "00FF00"}, {"owner": "Jane"}]
)
def test_update_service(
    data, client: TestClient, service_factory, admin_token_headers, api_version
):
    original_data = {
        "category": "My Service",
        "color": "FF0000",
        "owner": "John",
    }
    service = service_factory(**original_data)
    response = client.patch(
        f"/api/{api_version}/services/{service.id}",
        headers=admin_token_headers,
        json=data,
    )
    assert response.status_code == 200
    new_data = {**original_data, **data}
    new_data["id"] = str(service.id)
    assert response.json() == new_data


def test_read_service_notifications(
    client: TestClient,
    db,
    admin_token_headers,
    service,
    notification_factory,
    api_version,
):
    notification1 = notification_factory(service=service)
    notification2 = notification_factory(service=service)
    # extra notification not linked to service
    notification_factory()
    response = client.get(
        f"/api/{api_version}/services/{service.id}/notifications",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": notification1.id,
            "service_id": str(notification1.service_id),
            "subtitle": notification1.subtitle,
            "timestamp": notification1.timestamp.isoformat().rstrip("0"),
            "title": notification1.title,
            "url": notification1.url,
        },
        {
            "id": notification2.id,
            "service_id": str(notification2.service_id),
            "subtitle": notification2.subtitle,
            "timestamp": notification2.timestamp.isoformat().rstrip("0"),
            "title": notification2.title,
            "url": notification2.url,
        },
    ]


def test_read_service_notifications_invalid_service_id(
    client: TestClient, admin_token_headers, api_version
):
    response = client.get(
        f"/api/{api_version}/services/1234/notifications", headers=admin_token_headers
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "ctx": {
                    "error": "invalid length: expected length 32 for simple "
                    "format, found 4"
                },
                "loc": ["path", "service_id"],
                "input": "1234",
                "msg": "Input should be a valid UUID, invalid length: expected "
                "length 32 for simple format, found 4",
                "type": "uuid_parsing",
                "url": "https://errors.pydantic.dev/2.1/v/uuid_parsing",
            }
        ],
    }


def test_read_service_notifications_unknown_service_id(
    client: TestClient, admin_token_headers, api_version
):
    service_id = uuid.uuid4()
    response = client.get(
        f"/api/{api_version}/services/{service_id}/notifications",
        headers=admin_token_headers,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Service not found"}


def test_create_notification_for_service_ip_not_allowed(
    client: TestClient,
    service,
    user_token_headers,
    sample_notification,
    mocker,
    api_version,
):
    mocker.patch("app.api.services.utils.check_ips", return_value=False)
    response = client.post(
        f"/api/{api_version}/services/{service.id}/notifications",
        headers=user_token_headers,
        json=sample_notification,
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "IP address not allowed"}


def test_create_notification_for_service_unknown_service(
    client: TestClient, user_token_headers, sample_notification, mocker, api_version
):
    mocker.patch("app.api.services.utils.check_ips", return_value=True)
    service_id = uuid.uuid4()
    response = client.post(
        f"/api/{api_version}/services/{service_id}/notifications",
        headers=user_token_headers,
        json=sample_notification,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Service not found"}


def test_create_notification_for_service(
    client: TestClient,
    db,
    service,
    user_token_headers,
    sample_notification,
    mocker,
    api_version,
):
    mocker.patch("app.api.services.utils.check_ips", return_value=True)
    mock_send_notification = mocker.patch("app.api.services.utils.send_notification")
    response = client.post(
        f"/api/{api_version}/services/{service.id}/notifications",
        headers=user_token_headers,
        json=sample_notification,
    )
    assert response.status_code == 201
    db_notification = db.query(models.Notification).first()
    mock_send_notification.assert_called_once_with(db, db_notification)
    assert response.json() == {
        "id": db_notification.id,
        "service_id": str(service.id),
        "subtitle": sample_notification["subtitle"],
        "timestamp": db_notification.timestamp.isoformat().rstrip("0"),
        "title": sample_notification["title"],
        "url": sample_notification["url"],
    }
