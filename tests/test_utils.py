import pytest
from datetime import datetime, timedelta, timezone
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
    non_existing_id = notification1.id + notification2.id
    ios_token1 = make_device_token(64)
    ios_token2 = make_device_token(64)
    ios_token3 = make_device_token(64)
    ios_token4 = make_device_token(64)
    ios_token5 = make_device_token(64)
    android_token1 = make_device_token(128)
    android_token2 = make_device_token(128)
    android_token3 = make_device_token(128)
    android_token4 = make_device_token(128)
    android_token5 = make_device_token(128)
    expire_date = datetime.now(timezone.utc) + timedelta(minutes=60)
    user1 = user_factory(
        device_tokens=[ios_token1, ios_token2], login_token_expire_date=expire_date
    )
    user2 = user_factory(
        device_tokens=[ios_token3, android_token1], login_token_expire_date=expire_date
    )
    user3 = user_factory(
        device_tokens=[android_token2, android_token3],
        login_token_expire_date=expire_date,
    )
    user4 = user_factory(
        device_tokens=[ios_token5, android_token5],
        login_token_expire_date=datetime.now(timezone.utc) + timedelta(minutes=-1),
    )
    user5 = user_factory(
        device_tokens=[ios_token5, android_token5],
        login_token_expire_date=expire_date,
        is_active=False,
    )
    user_factory(device_tokens=[ios_token4, android_token4])
    user1.notifications.append(notification1)
    user1.notifications.append(notification2)
    user2.notifications.append(notification1)
    user3.notifications.append(notification1)
    user4.notifications.append(notification1)
    user5.notifications.append(notification1)
    db.commit()
    await utils.send_notification(notification1.id)
    # Check that send_push_to_ios was called 3 times
    # - twice for user1 (2 APN tokens)
    # - once for user2 (1 APN tokens)
    # - none for user4 as it is not logged in
    # - none for user5 as it is not active
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
    # Only keep second and third arguments (token and payload)
    # first arg is httpx client and others (db and user) are internal
    calls = [call.args[1:3] for call in mock_send_push_to_ios.call_args_list]
    expected_calls_args = [
        (ios_token1, user1_payload),
        (ios_token2, user1_payload),
        (ios_token3, user2_payload),
    ]
    assert calls == expected_calls_args
    # Check that send_push_to_android was called 3 times
    # - once for user2 (1 android token)
    # - twice for user3 (2 adnroid tokens)
    # - none for user4 as it is not logged in
    # - none for user5 as it is not active
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
    # Only keep second argument (payload)
    # first arg is httpx client and others (db and user) are internal
    calls = [(call.args[1],) for call in mock_send_push_to_android.call_args_list]
    expected_calls_args = [
        (user2_payload1,),
        (user3_payload1,),
        (user3_payload2,),
    ]
    assert calls == expected_calls_args

    # Check with invalid notification id
    # send_push_to_ios or android shouldn't be called
    mock_send_push_to_ios.reset_mock()
    mock_send_push_to_android.reset_mock()
    mock_get_firebase_access_token.reset_mock()
    await utils.send_notification(non_existing_id)
    assert mock_get_firebase_access_token.called
    assert not mock_send_push_to_ios.called
    assert not mock_send_push_to_android.called


def test_create_and_decode_access_token():
    username = "johndoe"
    encoded_token = utils.create_access_token(
        username, expire=datetime.now(timezone.utc) + timedelta(days=1)
    )
    decoded_token = utils.decode_access_token(encoded_token)
    assert decoded_token["sub"] == username
    # Token includes Expiration Time Claim
    assert "exp" in decoded_token
