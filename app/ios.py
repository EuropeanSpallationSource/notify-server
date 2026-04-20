import httpx
import jwt
from datetime import datetime
from typing import Dict, Optional
from fastapi.logger import logger
from . import schemas
from .settings import (
    APNS_ALGORITHM,
    APNS_AUTH_KEY,
    APNS_KEY_ID,
    TEAM_ID,
    BUNDLE_ID,
    APPLE_SERVER,
)


def create_headers(issued_at: datetime) -> Dict[str, str]:
    """Return the required headers to send an Apple push notification"""
    token = jwt.encode(
        {"iss": str(TEAM_ID), "iat": issued_at},
        str(APNS_AUTH_KEY),
        algorithm=APNS_ALGORITHM,
        headers={"alg": APNS_ALGORITHM, "kid": str(APNS_KEY_ID)},
    )
    return {
        "apns-expiration": "0",
        "apns-priority": "10",
        "apns-topic": BUNDLE_ID,
        "authorization": "Bearer " + token,
    }


async def send_push(
    client: httpx.AsyncClient,
    apn: str,
    payload: schemas.ApnPayload,
    username: str,
) -> Optional[str]:
    """Send a push notification to iOS

    Return the device token to remove if no longer valid, None otherwise
    """
    logger.info(f"Send notification to {username} (apn: {apn[:10]}...)")
    try:
        response = await client.post(
            f"https://{APPLE_SERVER}/3/device/{apn}", json=payload.model_dump()
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"HTTP Exception for {exc.request.url} - {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(f"{exc}")
        try:
            logger.warning(f"response: {response.json()}")
        except Exception:
            logger.warning("No json response content")
        # See https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/handling_notification_responses_from_apns
        if response.status_code == 410:
            logger.info(
                f"Device token no longer active. Delete {apn} for user {username}"
            )
            return apn
        return None
    logger.info(f"Notification sent to user {username}")
    return None
