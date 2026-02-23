import json
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
async def test_send_push_to_android_success(android_payload):
    request = respx.post(
        "https://fcm.googleapis.com/v1/projects/my-project/messages:send",
    )
    request.side_effect = httpx.Response(200)
    async with httpx.AsyncClient() as client:
        token_to_remove = await firebase.send_push(client, android_payload, "testuser")
    assert request.called
    req, _ = respx.calls[0]
    assert json.loads(req._content.decode("utf-8")) == android_payload.model_dump()
    assert token_to_remove is None


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
async def test_send_push_to_android_error(android_payload, side_effect):
    # No exception raised in case of error
    request = respx.post(
        "https://fcm.googleapis.com/v1/projects/my-project/messages:send",
    )
    request.side_effect = side_effect
    async with httpx.AsyncClient() as client:
        token_to_remove = await firebase.send_push(client, android_payload, "testuser")
    assert request.called
    assert token_to_remove is None


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_android_404(android_payload):
    device_token = android_payload.message.token
    request = respx.post(
        "https://fcm.googleapis.com/v1/projects/my-project/messages:send",
    )
    request.side_effect = httpx.Response(404, json={"error": "message"})
    async with httpx.AsyncClient() as client:
        token_to_remove = await firebase.send_push(client, android_payload, "testuser")
    assert request.called
    # Returns the token that should be removed
    assert token_to_remove == device_token
