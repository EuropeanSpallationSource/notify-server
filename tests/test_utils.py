import pytest
import httpx
import respx
from datetime import datetime
from app import schemas, utils


@pytest.fixture(scope="module")
def apn_payload():
    aps = schemas.Aps(
        alert=schemas.Alert(title="New alert", subtitle="This is a test"), badge=3
    )
    return schemas.ApnPayload(aps=aps)


@pytest.mark.parametrize(
    "ip,allowed_networks,expected",
    [
        ("192.168.1.2", [], True),
        ("192.168.1.2", ["192.168.1.0/24"], True),
        ("192.168.1", ["192.168.1.0/24"], False),
        ("192.168.1.4", ["192.168.2.0/24", "192.168.3.0/24"], False),
    ],
)
def test_is_ip_allowed(ip, allowed_networks, expected):
    assert utils.is_ip_allowed(ip, allowed_networks) is expected


@pytest.mark.parametrize(
    "ips,allowed_networks,expected",
    [
        (None, [], True),
        ([], [], True),
        (["foo"], [], True),
        (["192.168.0.2"], [], True),
        (None, ["192.168.1.0/24"], False),
        ([], ["192.168.1.0/24"], False),
        (["192.168.1.2"], ["192.168.1.0/24"], True),
        (["192.168.1.2", "172.30.4.11"], ["192.168.1.0/24", "172.30.4.0/24"], True),
        (["foo"], ["192.168.1.0/24"], False),
        ("[192.168.1]", ["192.168.1.0/24"], False),
        (["192.168.1.2", "172.30.4.11"], ["192.168.1.0/24", "172.30.5.0/24"], False),
        (["192.168.1.2", "172.30.4.11"], ["172.30.4.0/24"], False),
    ],
)
def test_check_ips(ips, allowed_networks, expected):
    assert utils.check_ips(ips, allowed_networks) is expected


def test_create_apn_headers():
    issued_at = datetime(2020, 11, 12, 9, 0)
    headers = utils.create_apn_headers(issued_at)
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
        notification_sent = await utils.send_push_to_ios(
            client, apn, apn_payload, db, user
        )
    assert request.called
    req, _ = respx.calls[0]
    assert req._content == apn_payload.json().encode("utf-8")
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
        notification_sent = await utils.send_push_to_ios(
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
        notification_sent = await utils.send_push_to_ios(
            client, device_token, apn_payload, db, user
        )
    assert request.called
    assert not notification_sent
    db.refresh(user)
    # No longer active token deleted
    assert user.device_tokens == []


@pytest.mark.asyncio
async def test_send_notification(db, user_factory, notification_factory, mocker):
    mock_send_push_to_ios = mocker.patch("app.utils.send_push_to_ios")
    notification1 = notification_factory()
    notification2 = notification_factory()
    user1 = user_factory(device_tokens=["user1-apn1", "user1-apn2"])
    user2 = user_factory(device_tokens=["user2-apn1"])
    user_factory(device_tokens=["user3-apn1"])
    user1.notifications.append(notification1)
    user1.notifications.append(notification2)
    user2.notifications.append(notification1)
    db.commit()
    await utils.send_notification(db, notification1)
    # Check that send_push_to_ios was called 3 times
    # - twice for user1 (2 APN tokens)
    # - once for user2 (1 APN tokens)
    assert mock_send_push_to_ios.call_count == 3
    user1_payload = schemas.ApnPayload(
        aps=schemas.Aps(
            alert=schemas.Alert(
                title=notification1.title, subtitle=notification1.subtitle
            ),
            badge=2,
        )
    )
    user2_payload = schemas.ApnPayload(
        aps=schemas.Aps(
            alert=schemas.Alert(
                title=notification1.title, subtitle=notification1.subtitle
            ),
            badge=1,
        )
    )
    # Remove the first arg (httpx client) from the list of calls
    calls = [call.args[1:] for call in mock_send_push_to_ios.call_args_list]
    expected_calls_args = [
        ("user1-apn1", user1_payload, db, user1),
        ("user1-apn2", user1_payload, db, user1),
        ("user2-apn1", user2_payload, db, user2),
    ]
    assert calls == expected_calls_args


def test_create_and_decode_access_token():
    username = "johndoe"
    encoded_token = utils.create_access_token(username)
    decoded_token = utils.decode_access_token(encoded_token)
    assert decoded_token["sub"] == username
    # Token includes Expiration Time Claim
    assert "exp" in decoded_token
