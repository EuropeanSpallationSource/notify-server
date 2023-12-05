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
async def test_send_push_to_ios_success(db, user, apn_payload):
    apn = "apn-token"
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{apn}",
    )
    request.side_effect = httpx.Response(200)
    async with httpx.AsyncClient(http2=True) as client:
        notification_sent = await ios.send_push(client, apn, apn_payload, db, user)
    assert request.called
    req, _ = respx.calls[0]
    assert json.loads(req._content.decode("utf-8")) == apn_payload.model_dump()
    assert notification_sent


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
async def test_send_push_to_ios_error(db, user_factory, apn_payload, side_effect):
    # No exception raised in case of error
    device_token = "my-token"
    user = user_factory(device_tokens=[device_token])
    assert user.device_tokens == [device_token]
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{device_token}",
    )
    request.side_effect = side_effect
    async with httpx.AsyncClient(http2=True) as client:
        notification_sent = await ios.send_push(
            client, device_token, apn_payload, db, user
        )
    assert request.called
    assert not notification_sent
    db.refresh(user)
    assert user.device_tokens == [device_token]


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_ios_410(db, user_factory, apn_payload):
    device_token = "my-token"
    user = user_factory(device_tokens=[device_token])
    assert user.device_tokens == [device_token]
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{device_token}",
    )
    request.side_effect = httpx.Response(410)
    async with httpx.AsyncClient(http2=True) as client:
        notification_sent = await ios.send_push(
            client, device_token, apn_payload, db, user
        )
    assert request.called
    assert not notification_sent
    db.refresh(user)
    # No longer active token deleted
    assert user.device_tokens == []
