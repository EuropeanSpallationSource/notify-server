import asyncio
import httpx
import ipaddress
import uuid
import jwt
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from . import models, ios, firebase
from .settings import (
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


async def send_notification(db: Session, notification: models.Notification) -> None:
    """Send the notification to all subscribers"""
    ios_headers = ios.create_headers(datetime.utcnow())
    ios_client = httpx.AsyncClient(http2=True, headers=ios_headers)
    tasks = [
        ios.send_push(
            ios_client,
            ios_token,
            user_notification.to_apn_payload(),
            db,
            user_notification.user,
        )
        for user_notification in notification.users_notification
        for ios_token in user_notification.user.ios_tokens
    ]
    android_headers = await firebase.create_headers(str(uuid.uuid4()))
    android_client = httpx.AsyncClient(headers=android_headers)
    tasks.extend(
        [
            firebase.send_push(
                android_client,
                user_notification.to_android_payload(android_token),
                db,
                user_notification.user,
            )
            for user_notification in notification.users_notification
            for android_token in user_notification.user.android_tokens
        ]
    )
    await gather_with_concurrency(NB_PARALLEL_PUSH, *tasks, return_exceptions=True)
    await ios_client.aclose()
    await android_client.aclose()
