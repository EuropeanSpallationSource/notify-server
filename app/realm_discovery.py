"""
Realm discovery utilities for automatic Keycloak realm selection based on username.
"""

from urllib.parse import urlencode
from .settings import (
    OIDC_BASE_URL,
    OIDC_DEFAULT_REALM,
    OIDC_CLIENT_ID,
    OIDC_CLIENT_SECRET,
    OIDC_SCOPE,
    OIDC_REALM_MAPPING,
)
from .schemas import RealmType


def discover_realm(realm_type: RealmType) -> str:
    """
    Discover the appropriate Keycloak realm for a given username.

    Args:
        realm_type: The realm type to check for realm mapping

    Returns:
        The realm name to use for this realm type
    """

    # Check realm mapping configuration
    for mapping in OIDC_REALM_MAPPING:
        if ":" in mapping:
            pattern, realm = mapping.split(":", 1)
            pattern = pattern.strip().lower()
            realm = realm.strip()

            # Check if pattern matches realm_type
            if pattern == realm_type.lower().strip():
                return realm

    # Default realm fallback
    return OIDC_DEFAULT_REALM


def get_keycloak_auth_url(
    realm: str, username: str, redirect_uri: str, state: str
) -> str:
    """
    Generate Keycloak authorization URL for a specific realm with username pre-filled.

    Args:
        realm: The Keycloak realm name
        username: The username to pre-fill
        redirect_uri: The redirect URI after authentication
        state: OAuth state parameter

    Returns:
        Complete Keycloak authorization URL
    """
    auth_endpoint = get_keycloak_authorization_endpoint(realm)

    params = {
        "response_type": "code",
        "client_id": OIDC_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": OIDC_SCOPE,
        "state": state,
        "login_hint": username,  # Pre-fill username in Keycloak login form
    }

    return f"{auth_endpoint}?{urlencode(params)}"


def get_keycloak_issuer(realm: str) -> str:
    """
    Get the userinfo endpoint URL for a specific realm.

    Args:
        realm: The Keycloak realm name

    Returns:
        Userinfo endpoint URL
    """
    return f"{OIDC_BASE_URL.rstrip('/')}/realms/{realm}"


def get_keycloak_token_endpoint(realm: str) -> str:
    """
    Get the token endpoint URL for a specific realm.

    Args:
        realm: The Keycloak realm name

    Returns:
        Token endpoint URL
    """
    return f"{OIDC_BASE_URL.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"


def get_keycloak_authorization_endpoint(realm: str) -> str:
    """
    Get the userinfo endpoint URL for a specific realm.

    Args:
        realm: The Keycloak realm name

    Returns:
        Userinfo endpoint URL
    """
    return f"{OIDC_BASE_URL.rstrip('/')}/realms/{realm}/protocol/openid-connect/auth"


def get_keycloak_userinfo_endpoint(realm: str) -> str:
    """
    Get the userinfo endpoint URL for a specific realm.

    Args:
        realm: The Keycloak realm name

    Returns:
        Userinfo endpoint URL
    """
    return (
        f"{OIDC_BASE_URL.rstrip('/')}/realms/{realm}/protocol/openid-connect/userinfo"
    )


def get_client_secret() -> str:
    """
    Get the OIDC client secret.

    Returns:
        The client secret as a string
    """
    return str(OIDC_CLIENT_SECRET)
