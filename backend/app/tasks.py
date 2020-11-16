import httpx
import jwt
from datetime import datetime
from . import models, schemas
from .settings import (
    ALGORITHM,
    APNS_AUTH_KEY,
    APNS_KEY_ID,
    TEAM_ID,
    BUNDLE_ID,
    APPLE_SERVER,
)


async def send_push_to_ios(apn: str, payload: schemas.ApnPayload) -> None:
    token = jwt.encode(
        {"iss": str(TEAM_ID), "iat": datetime.utcnow()},
        str(APNS_AUTH_KEY),
        algorithm=ALGORITHM,
        headers={"alg": ALGORITHM, "kid": str(APNS_KEY_ID)},
    )
    headers = {
        "apns-expiration": "0",
        "apns-priority": "10",
        "apns-topic": BUNDLE_ID,
        "authorization": f"Bearer {token.decode('ascii')}",
    }
    url = f"https://{APPLE_SERVER}/3/device/{apn}"
    async with httpx.AsyncClient(http2=True) as client:
        await client.post(url, json=payload.dict(), headers=headers)


async def send_notification(notification: models.Notification) -> None:
    for user_notification in notification.users_notification:
        apn_payload = user_notification.to_apn_payload()
        for apn_token in user_notification.user.apn_tokens:
            await send_push_to_ios(apn_token, apn_payload)
