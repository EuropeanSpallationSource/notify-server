import httpx
import ldap3
from fastapi.logger import logger
from .settings import (
    AUTHENTICATION_METHOD,
    AUTHENTICATION_URL,
    LDAP_HOST,
    LDAP_PORT,
    LDAP_USE_SSL,
    LDAP_USER_RDN_ATTR,
    LDAP_BASE_DN,
    LDAP_USER_DN,
)


def authenticate_user(username: str, password: str) -> bool:
    """Return True if the authentication is successful, False otherwise"""
    if AUTHENTICATION_METHOD == "ldap":
        return ldap_authenticate_user(username, password)
    elif AUTHENTICATION_METHOD == "url":
        return url_authenticate_user(username, password)
    else:
        logger.error(f"Invalid authentication method: {AUTHENTICATION_METHOD}")
        return False


def ldap_authenticate_user(username: str, password: str) -> bool:
    """Return True if the LDAP authentication is successful, False otherwise

    Authentication is checked using a direct bind
    """
    server = ldap3.Server(LDAP_HOST, port=LDAP_PORT, use_ssl=LDAP_USE_SSL)
    if LDAP_USER_DN:
        user_search_dn = f"{LDAP_USER_DN},{LDAP_BASE_DN}"
    else:
        user_search_dn = LDAP_BASE_DN
    bind_user = f"{LDAP_USER_RDN_ATTR}={username},{user_search_dn}"
    connection = ldap3.Connection(
        server=server,
        user=bind_user,
        password=password,
        client_strategy=ldap3.SYNC,
        authentication="SIMPLE",
        raise_exceptions=False,
    )
    result = connection.bind()
    connection.unbind()
    return result


def url_authenticate_user(username: str, password: str) -> bool:
    """Return True if the authentication is successful, False otherwise

    Authentication is checked using a POST request to a dedicated service
    """
    payload = {"username": username, "password": password}
    try:
        response = httpx.post(AUTHENTICATION_URL, json=payload)
        response.raise_for_status()
    except httpx.RequestError as exc:
        logger.error(f"HTTP Exception for {exc.request.url} - {exc}")
        return False
    except httpx.HTTPStatusError as exc:
        logger.warning(f"{exc}")
        return False
    return True
