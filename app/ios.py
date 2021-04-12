import httpx
import jwt
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session
from fastapi.logger import logger
from . import models, schemas, crud
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
    db: Session,
    user: models.User,
) -> bool:
    """Send a push notification to iOS

    Return True in case of success
    """
    logger.info(f"Send notification to {user.username} (apn: {apn[:10]}...)")
    try:
        response = await client.post(
            f"https://{APPLE_SERVER}/3/device/{apn}", json=payload.dict()
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"HTTP Exception for {exc.request.url} - {exc}")
        return False
    except httpx.HTTPStatusError as exc:
        logger.warning(f"{exc}")
        if response.status_code == 410:
            logger.info(
                f"Device token no longer active. Delete {apn} for user {user.username}"
            )
            crud.remove_user_device_token(db, user, apn)
        return False
    logger.info(f"Notification sent to user {user.username}")
    return True
