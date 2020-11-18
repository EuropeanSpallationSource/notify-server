import pytest
import respx
from app import schemas, utils
from unittest import mock


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


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_ios():
    apn = "apn-token"
    aps = schemas.Aps(
        alert=schemas.Alert(title="New alert", subtitle="This is a test"), badge=3
    )
    payload = schemas.ApnPayload(aps=aps)
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{apn}",
    )
    await utils.send_push_to_ios(apn, payload)
    assert request.called
    req, _ = respx.calls[0]
    assert req.headers["apns-expiration"] == "0"
    assert req.headers["apns-priority"] == "10"
    assert req.headers["apns-topic"] == "eu.ess.ESS-Notify"
    assert req.headers["Authorization"].startswith("Bearer")
    assert req._content == payload.json().encode("utf-8")


@pytest.mark.asyncio
async def test_send_notification(db, user_factory, notification_factory, mocker):
    mock_send_push_to_ios = mocker.patch("app.utils.send_push_to_ios")
    notification1 = notification_factory()
    notification2 = notification_factory()
    user1 = user_factory(apn_tokens=["user1-apn1", "user1-apn2"])
    user2 = user_factory(apn_tokens=["user2-apn1"])
    user_factory(apn_tokens=["user3-apn1"])
    user1.notifications.append(notification1)
    user1.notifications.append(notification2)
    user2.notifications.append(notification1)
    db.commit()
    await utils.send_notification(notification1)
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
    calls = [
        mock.call("user1-apn1", user1_payload),
        mock.call("user1-apn2", user1_payload),
        mock.call("user2-apn1", user2_payload),
    ]
    mock_send_push_to_ios.assert_has_calls(calls)
