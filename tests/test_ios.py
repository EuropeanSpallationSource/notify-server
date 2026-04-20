import json
import pytest
import httpx
import respx
from datetime import datetime
from app import schemas, ios


@pytest.fixture(scope="module")
def apn_payload():
    aps = schemas.Aps(
        alert=schemas.Alert(title="New alert", subtitle="This is a test"), badge=3
    )
    return schemas.ApnPayload(aps=aps)


def test_create_headers():
    issued_at = datetime(2020, 11, 12, 9, 0)
    headers = ios.create_headers(issued_at)
    assert set(headers.keys()) == {
        "apns-expiration",
        "apns-priority",
        "apns-topic",
        "authorization",
    }
    assert headers["apns-expiration"] == "0"
    assert headers["apns-priority"] == "10"
    assert headers["apns-topic"] == "eu.ess.ESS-Notify"
    assert headers["authorization"].startswith("Bearer")


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_ios_success(apn_payload):
    apn = "apn-token"
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{apn}",
    )
    request.side_effect = httpx.Response(200)
    async with httpx.AsyncClient(http2=True) as client:
        token_to_remove = await ios.send_push(client, apn, apn_payload, "testuser")
    assert request.called
    req, _ = respx.calls[0]
    assert json.loads(req._content.decode("utf-8")) == apn_payload.model_dump()
    assert token_to_remove is None


@respx.mock
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect",
    [
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.Response(400),
        httpx.Response(403),
        httpx.Response(405),
        httpx.Response(500),
        httpx.Response(429),
    ],
)
async def test_send_push_to_ios_error(apn_payload, side_effect):
    # No exception raised in case of error
    device_token = "my-token"
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{device_token}",
    )
    request.side_effect = side_effect
    async with httpx.AsyncClient(http2=True) as client:
        token_to_remove = await ios.send_push(
            client, device_token, apn_payload, "testuser"
        )
    assert request.called
    assert token_to_remove is None


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_ios_410(apn_payload):
    device_token = "my-token"
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{device_token}",
    )
    request.side_effect = httpx.Response(410)
    async with httpx.AsyncClient(http2=True) as client:
        token_to_remove = await ios.send_push(
            client, device_token, apn_payload, "testuser"
        )
    assert request.called
    # Returns the token that should be removed
    assert token_to_remove == device_token
