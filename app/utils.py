import asyncio
import httpx
import ipaddress
import uuid
import jwt
from datetime import datetime, timezone
from typing import List, Optional, Dict
from fastapi.logger import logger
from .database import SessionLocal
from . import crud, ios, firebase
from .settings import (
    ALLOWED_NETWORKS,
    SECRET_KEY,
    JWT_ALGORITHM,
    NB_PARALLEL_PUSH,
)


def create_access_token(username: str, expire: datetime) -> str:
    """Encode the data as JWT, including the expiration time claim"""
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, str(SECRET_KEY), algorithm=JWT_ALGORITHM)
    return encoded_jwt


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


async def send_notification(notification_id: int) -> None:
    """Send the notification to all subscribers"""
    tasks = []
    ios_headers = ios.create_headers(datetime.now(timezone.utc))
    ios_client = httpx.AsyncClient(http2=True, headers=ios_headers)
    android_headers = await firebase.create_headers(str(uuid.uuid4()))
    android_client = httpx.AsyncClient(headers=android_headers)
    try:
        db = SessionLocal()
        notification = crud.get_notification(db, notification_id)
        if notification is None:
            logger.warning(
                f"Can't send notification! Notification {notification_id} not found."
            )
            return
        for user_notification in notification.users_notification:
            user = user_notification.user
            if not user.is_logged_in or not user.is_active:
                continue
            ios_tokens = user.ios_tokens
            if ios_tokens:
                apn_payload = user_notification.to_apn_payload()
                for ios_token in ios_tokens:
                    tasks.append(
                        ios.send_push(
                            ios_client,
                            ios_token,
                            apn_payload,
                            db,
                            user,
                        )
                    )
            for android_token in user.android_tokens:
                tasks.append(
                    firebase.send_push(
                        android_client,
                        user_notification.to_android_payload(android_token),
                        db,
                        user,
                    )
                )
        await gather_with_concurrency(NB_PARALLEL_PUSH, *tasks, return_exceptions=True)
        await ios_client.aclose()
        await android_client.aclose()
    finally:
        db.close()
