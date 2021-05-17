import pytest
from app import schemas, utils


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


@pytest.mark.asyncio
async def test_send_notification(
    db, user_factory, notification_factory, make_device_token, mocker
):
    mock_send_push_to_ios = mocker.patch("app.ios.send_push")
    mock_send_push_to_android = mocker.patch("app.firebase.send_push")
    mock_get_firebase_access_token = mocker.patch(
        "app.firebase.get_access_token", return_value="my-token"
    )
    notification1 = notification_factory()
    notification2 = notification_factory()
    ios_token1 = make_device_token(64)
    ios_token2 = make_device_token(64)
    ios_token3 = make_device_token(64)
    ios_token4 = make_device_token(64)
    android_token1 = make_device_token(128)
    android_token2 = make_device_token(128)
    android_token3 = make_device_token(128)
    android_token4 = make_device_token(128)
    user1 = user_factory(device_tokens=[ios_token1, ios_token2])
    user2 = user_factory(device_tokens=[ios_token3, android_token1])
    user3 = user_factory(device_tokens=[android_token2, android_token3])
    user_factory(device_tokens=[ios_token4, android_token4])
    user1.notifications.append(notification1)
    user1.notifications.append(notification2)
    user2.notifications.append(notification1)
    user3.notifications.append(notification1)
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
        (ios_token1, user1_payload, db, user1),
        (ios_token2, user1_payload, db, user1),
        (ios_token3, user2_payload, db, user2),
    ]
    assert calls == expected_calls_args
    # Check that send_push_to_android was called 3 times
    # - once for user2 (1 android token)
    # - twice for user3 (2 adnroid tokens)
    assert mock_get_firebase_access_token.call_count == 1
    assert mock_send_push_to_android.call_count == 3
    user2_payload1 = schemas.AndroidPayload(
        message=schemas.AndroidMessage(
            token=android_token1,
            data=schemas.AndroidData(
                title=notification1.title,
                body=notification1.subtitle,
                url=notification1.url,
            ),
        )
    )
    user3_payload1 = schemas.AndroidPayload(
        message=schemas.AndroidMessage(
            token=android_token2,
            data=schemas.AndroidData(
                title=notification1.title,
                body=notification1.subtitle,
                url=notification1.url,
            ),
        )
    )
    user3_payload2 = schemas.AndroidPayload(
        message=schemas.AndroidMessage(
            token=android_token3,
            data=schemas.AndroidData(
                title=notification1.title,
                body=notification1.subtitle,
                url=notification1.url,
            ),
        )
    )
    # Remove the first arg (httpx client) from the list of calls
    calls = [call.args[1:] for call in mock_send_push_to_android.call_args_list]
    expected_calls_args = [
        (user2_payload1, db, user2),
        (user3_payload1, db, user3),
        (user3_payload2, db, user3),
    ]
    assert calls == expected_calls_args


def test_create_and_decode_access_token():
    username = "johndoe"
    encoded_token = utils.create_access_token(username)
    decoded_token = utils.decode_access_token(encoded_token)
    assert decoded_token["sub"] == username
    # Token includes Expiration Time Claim
    assert "exp" in decoded_token
