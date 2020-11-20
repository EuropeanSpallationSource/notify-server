import asyncio
import httpx
import ipaddress
import jwt
from datetime import datetime, timedelta
from typing import List, Optional, Dict
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
    ALLOWED_NETWORKS,
    SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    NB_PARALLEL_PUSH,
)


def create_access_token(
    username: str, expires_delta_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES
) -> str:
    """Encode the data as JWT, including the expiration time claim"""
    expire = datetime.utcnow() + timedelta(minutes=expires_delta_minutes)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, str(SECRET_KEY), algorithm=JWT_ALGORITHM)
    return encoded_jwt.decode("utf-8")


def decode_access_token(encoded_token: str) -> Dict:
    return jwt.decode(encoded_token, str(SECRET_KEY), algorithms=[JWT_ALGORITHM])


def check_ips(
    ips: Optional[List[str]] = None, allowed_networks: List[str] = ALLOWED_NETWORKS
) -> bool:
    """Return True if all ip addresses are in the list of allowed networks

    Any IP is allowed if the list is empty
    """
    if not allowed_networks:
        return True
    if ips is None or not ips:
        # No IP to check
        return False
    return all([is_ip_allowed(ip, allowed_networks) for ip in ips])


def is_ip_allowed(ip: str, allowed_networks: List[str]) -> bool:
    """Return True if the ip is in the list of allowed networks

    Any IP is allowed if the list is empty
    """
    if not allowed_networks:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        # Invalid IP
        return False
    for allowed_network in allowed_networks:
        if addr in ipaddress.ip_network(allowed_network):
            return True
    return False


async def gather_with_concurrency(n: int, *tasks, return_exceptions=True):
    """Gather all the tasks with a maximum of n in parallel"""
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task

    return await asyncio.gather(
        *(sem_task(task) for task in tasks), return_exceptions=return_exceptions
    )


async def send_push_to_ios(
    client: httpx.AsyncClient,
    apn: str,
    payload: schemas.ApnPayload,
    db: Session,
    user: models.User,
) -> bool:
    """Send a push notification to iOS

    Return True in case of success
    """
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
            crud.remove_user_apn_token(db, user, apn)
        return False
    logger.info(f"Notification sent to user {user.username}")
    return True


def create_apn_headers(issued_at: datetime) -> Dict[str, str]:
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
        "authorization": f"Bearer {token.decode('utf-8')}",
    }


async def send_notification(db: Session, notification: models.Notification) -> None:
    """Send the notification to all subscribers"""
    headers = create_apn_headers(datetime.utcnow())
    client = httpx.AsyncClient(http2=True, headers=headers)
    tasks = [
        send_push_to_ios(
            client,
            apn_token,
            user_notification.to_apn_payload(),
            db,
            user_notification.user,
        )
        for user_notification in notification.users_notification
        for apn_token in user_notification.user.apn_tokens
    ]
    await gather_with_concurrency(NB_PARALLEL_PUSH, *tasks, return_exceptions=True)
    await client.aclose()
