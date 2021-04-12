import httpx
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from fastapi.logger import logger
from typing import Dict
from . import models, schemas, crud
from .settings import GOOGLE_APPLICATION_CREDENTIALS, FIREBASE_PROJECT_ID


google_credentials = service_account.Credentials.from_service_account_file(
    filename=str(GOOGLE_APPLICATION_CREDENTIALS),
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


def get_access_token() -> str:
    """Retrieve a valid access token that can be used to authorize firebase requests."""
    if google_credentials.valid:
        return google_credentials.token
    request = GoogleRequest()
    google_credentials.refresh(request)
    return google_credentials.token


async def create_headers(request_id: str) -> Dict:
    """Prepare HTTP headers that will be used to request Firebase Cloud Messaging."""
    access_token: str = await run_in_threadpool(get_access_token)
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
        "X-Request-Id": request_id,
    }


async def send_push(
    client: httpx.AsyncClient,
    payload: schemas.AndroidPayload,
    db: Session,
    user: models.User,
) -> bool:
    """Send a push notification to Android

    Return True in case of success
    """
    device_token = payload.message.token
    logger.info(f"Send notification to {user.username} (token: {device_token[:10]}...)")
    try:
        response = await client.post(
            f"https://fcm.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/messages:send",
            json=payload.dict(),
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"HTTP Exception for {exc.request.url} - {exc}")
        return False
    except httpx.HTTPStatusError as exc:
        logger.warning(f"{exc}")
        logger.warning(response.json())
        if response.status_code in (400, 404):
            logger.info(
                f"Device token invalid or no longer active. Delete {device_token} for user {user.username}"
            )
            crud.remove_user_device_token(db, user, device_token)
        return False
    logger.info(f"Notification sent to user {user.username}")
    return True
