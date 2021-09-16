import pytest
import httpx
import respx
from app import schemas, firebase


@pytest.fixture(scope="module")
def android_payload():
    return schemas.AndroidPayload(
        message=schemas.AndroidMessage(
            token="my-token",
            data=schemas.AndroidData(title="My alert", body="this is a test", url=""),
        )
    )


@pytest.mark.asyncio
async def test_create_headers(mocker):
    request_id = "5a3d2400-5552-4667-867a-9dc359ba1120"
    access_token = "my-token"
    mock_get_firebase_access_token = mocker.patch(
        "app.firebase.get_access_token", return_value=access_token
    )
    headers = await firebase.create_headers(request_id)
    assert mock_get_firebase_access_token.call_count == 1
    assert headers == {
        "X-Request-Id": request_id,
        "Content-Type": "application/json; UTF-8",
        "Authorization": f"Bearer {access_token}",
    }


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_android_success(db, user, android_payload):
    request = respx.post(
        "https://fcm.googleapis.com/v1/projects/my-project/messages:send",
    )
    request.side_effect = httpx.Response(200)
    async with httpx.AsyncClient() as client:
        notification_sent = await firebase.send_push(client, android_payload, db, user)
    assert request.called
    req, _ = respx.calls[0]
    assert req._content == android_payload.json().encode("utf-8")
    assert notification_sent


@respx.mock
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect",
    [
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.Response(400, json={"error": "Request contains an invalid argument"}),
        httpx.Response(403, json={"error": "message"}),
        httpx.Response(405, json={"error": "message"}),
        httpx.Response(500, json={"error": "message"}),
        httpx.Response(429, json={"error": "message"}),
    ],
)
async def test_send_push_to_android_error(
    db, user_factory, android_payload, side_effect
):
    device_token = android_payload.message.token
    user = user_factory(device_tokens=[device_token])
    assert user.device_tokens == [device_token]
    # No exception raised in case of error
    request = respx.post(
        "https://fcm.googleapis.com/v1/projects/my-project/messages:send",
    )
    request.side_effect = side_effect
    async with httpx.AsyncClient() as client:
        notification_sent = await firebase.send_push(client, android_payload, db, user)
    assert request.called
    assert not notification_sent
    # Device token still present
    db.refresh(user)
    assert user.device_tokens == [device_token]


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_android_404(
    db,
    user_factory,
    android_payload,
):
    device_token = android_payload.message.token
    user = user_factory(device_tokens=[device_token])
    assert user.device_tokens == [device_token]
    request = respx.post(
        "https://fcm.googleapis.com/v1/projects/my-project/messages:send",
    )
    request.side_effect = httpx.Response(404, json={"error": "message"})
    async with httpx.AsyncClient() as client:
        notification_sent = await firebase.send_push(client, android_payload, db, user)
    assert request.called
    assert not notification_sent
    db.refresh(user)
    # No longer active or invalid token deleted
    assert user.device_tokens == []
