import asyncio
import base64
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


def matches_user_filter(notification, user, db) -> bool:
    """Check if notification matches user's filter for this service

    Returns True if notification should be sent to user
    """
    filter_record = crud.get_user_service_filter(db, user.id, notification.service_id)
    if not filter_record:
        return True  # No filter = send all

    text = f"{notification.title} {notification.subtitle}".lower()

    # Check exclusions first (highest priority)
    if filter_record.exclude_keywords:
        for keyword in filter_record.exclude_keywords.split(";"):
            keyword = keyword.strip()
            if keyword and keyword.lower() in text:
                logger.debug(
                    f"Notification {notification.id} excluded for user {user.username} "
                    f"(matched exclude keyword: '{keyword}')"
                )
                return False

    # Check inclusions (empty = include all)
    if filter_record.include_keywords:
        for keyword in filter_record.include_keywords.split(";"):
            keyword = keyword.strip()
            if keyword and keyword.lower() in text:
                return True
        # Has include list but no match
        logger.debug(
            f"Notification {notification.id} filtered for user {user.username} "
            f"(no include keywords matched)"
        )
        return False

    return True


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

            # Check user's filter settings
            if not matches_user_filter(notification, user, db):
                logger.info(
                    f"Notification {notification.id} filtered for user {user.username}"
                )
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


def validate_id_token(
    id_token: str,
    access_token: str,
    jwks_client: jwt.PyJWKClient,
    signing_algos: list[str],
    client_id: str,
) -> None:
    """Raise an exception if the validation of the id token fails"""
    # See https://pyjwt.readthedocs.io/en/stable/usage.html#oidc-login-flow
    signing_key = jwks_client.get_signing_key_from_jwt(id_token)
    # Decode and verify id_token claims
    # expiration, issued at, not before, audience and issuer
    data = jwt.decode_complete(
        id_token,
        key=signing_key,
        audience=client_id,
        algorithms=signing_algos,
        require=["exp", "iat", "nbf", "aud", "iss"],
        verify_signature=True,
    )
    payload, header = data["payload"], data["header"]
    alg_obj = jwt.get_algorithm_by_name(header["alg"])
    # compute at_hash, then validate
    # access_token must be bytes (not str)
    digest = alg_obj.compute_hash_digest(access_token.encode("utf-8"))
    at_hash = (
        base64.urlsafe_b64encode(digest[: (len(digest) // 2)])
        .rstrip(b"=")
        .decode("utf-8")
    )
    if at_hash != payload["at_hash"]:
        raise ValueError(
            f"at_hash value {payload['at_hash']} doesn't match computed {at_hash}"
        )


async def backfill_and_notify(user_id: int, service_ids: List[uuid.UUID]) -> None:
    """
    Backfill notification history for newly subscribed services and send
    a single summary push notification.

    This is called as a background task when a user subscribes to new services.
    """
    db = SessionLocal()
    try:
        user = crud.get_user(db, user_id)
        if not user or not user.is_logged_in or not user.is_active:
            logger.warning(
                f"Skipping backfill for user {user_id}: user not found or inactive"
            )
            return

        total_backfilled = 0
        service_names = []

        for service_id in service_ids:
            service = crud.get_service(db, service_id)
            if not service:
                logger.warning(f"Service {service_id} not found, skipping backfill")
                continue

            # Backfill notifications for this service
            count = crud.backfill_service_notifications(db, user, service)
            if count > 0:
                total_backfilled += count
                service_names.append(service.category)

        # Send one summary push notification if any notifications were backfilled
        if total_backfilled > 0:
            await send_summary_notification(user, total_backfilled, service_names)
            logger.info(
                f"Backfilled {total_backfilled} notifications for user {user.username} "
                f"across services: {', '.join(service_names)}"
            )
        else:
            logger.info(f"No notifications to backfill for user {user.username}")

    except Exception as e:
        logger.error(f"Error during backfill for user {user_id}: {e}", exc_info=True)
    finally:
        db.close()


async def send_summary_notification(
    user, notification_count: int, service_names: List[str]
) -> None:
    """Send a single push notification summarizing the backfilled notifications"""
    # Create summary message
    if len(service_names) == 1:
        title = f"Welcome to {service_names[0]}"
        body = f"{notification_count} notification{'s' if notification_count > 1 else ''} available"
    else:
        title = "New subscriptions"
        body = f"{notification_count} notifications from {len(service_names)} services"

    # Prepare iOS and Android clients
    ios_headers = ios.create_headers(datetime.now(timezone.utc))
    ios_client = httpx.AsyncClient(http2=True, headers=ios_headers)
    android_headers = await firebase.create_headers(str(uuid.uuid4()))
    android_client = httpx.AsyncClient(headers=android_headers)

    tasks = []

    try:
        # Send to iOS devices
        ios_tokens = user.ios_tokens
        if ios_tokens:
            from . import schemas

            apn_payload = schemas.ApnPayload(
                aps=schemas.Aps(
                    alert=schemas.Alert(title=title, body=body),
                    badge=user.nb_unread_notifications,
                )
            )
            for ios_token in ios_tokens:
                tasks.append(
                    ios.send_push(ios_client, ios_token, apn_payload, None, user)
                )

        # Send to Android devices
        for android_token in user.android_tokens:
            from . import schemas

            android_payload = schemas.AndroidPayload(
                message=schemas.AndroidMessage(
                    token=android_token,
                    data=schemas.AndroidData(
                        title=title,
                        body=body,
                        category="summary",
                        timestamp=str(int(datetime.now(timezone.utc).timestamp())),
                    ),
                )
            )
            tasks.append(
                firebase.send_push(android_client, android_payload, None, user)
            )

        # Execute all push notifications
        await gather_with_concurrency(NB_PARALLEL_PUSH, *tasks, return_exceptions=True)

    finally:
        await ios_client.aclose()
        await android_client.aclose()
