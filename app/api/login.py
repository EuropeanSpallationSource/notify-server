import httpx
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.logger import logger
from sqlalchemy.orm import Session
from .. import deps, crud, utils, auth, schemas
from ..settings import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    OIDC_CLIENT_SECRET,
    OIDC_SCOPE,
    OIDC_ENABLED,
    OIDC_BASE_URL,
    OIDC_REALM_MAPPING,
    OIDC_DEFAULT_REALM,
)

router = APIRouter()


def create_access_token(db, username, response) -> dict[str, str]:
    db_user = crud.get_user_by_username(db, username)
    if db_user is None:
        db_user = crud.create_user(db, username)
        response.status_code = status.HTTP_201_CREATED
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(db_user.username, expire=expire)
    crud.update_user_login_token_expire_date(db, db_user, expire)
    logger.info(f"User {username} successfully logged in")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Login using username/password"""
    username = form_data.username.lower()
    if not auth.authenticate_user(username, form_data.password):
        logger.warning(f"Authentication failed for {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    return create_access_token(db, username, response)


@router.post("/open_id_connect", status_code=status.HTTP_200_OK)
async def open_id_connect(
    oidc_auth: schemas.OpenIdConnectAuth,
    response: Response,
    request: Request,
    realm: schemas.RealmType,
    db: Session = Depends(deps.get_db),
):
    """Login using OpenID Connect Authentication Code flow from mobile client"""
    oidc_config = request.state.oidc_config[realm]
    data = {
        "client_id": oidc_auth.client_id,
        "client_secret": OIDC_CLIENT_SECRET,
        "code": oidc_auth.code,
        "code_verifier": oidc_auth.code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": oidc_auth.redirect_uri,
    }
    logger.info(
        "Login via OIDC Authentication Code flow. "
        f"Sending {data} to {oidc_config['token_endpoint']} to retrieve token."
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                oidc_config["token_endpoint"],
                data=data,
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            logger.error(
                f"An error occurred while requesting {exc.request.url!r}: {exc}."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"An error occurred while requesting {exc.request.url!r}",
            )
        except httpx.HTTPStatusError as exc:
            logger.error(f"Failed to get OIDC token: {response.content}")
            raise HTTPException(
                status_code=exc.response.status_code, detail="Failed to get OIDC token"
            )
        result = response.json()
        access_token = result["access_token"]
        id_token = result["id_token"]
        logger.debug("Retrieved access and id tokens. Validating id_token.")
        try:
            utils.validate_id_token(
                id_token,
                access_token,
                request.state.jwks_client,
                request.state.oidc_config["id_token_signing_alg_values_supported"],
                oidc_auth.client_id,
            )
        except Exception as e:
            logger.warning(f"id_token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="id_token validation failed",
            )
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {
            "client_id": oidc_auth.client_id,
            "client_secret": OIDC_CLIENT_SECRET,
            "scope": OIDC_SCOPE,
        }
        logger.info("Retrieving user info.")
        try:
            response = await client.post(
                oidc_config["userinfo_endpoint"],
                headers=headers,
                data=data,
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            logger.error(
                f"An error occurred while requesting {exc.request.url!r}: {exc}."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"An error occurred while requesting {exc.request.url!r}",
            )
        except httpx.HTTPStatusError as exc:
            logger.error(f"Failed to get user info: {response.content}")
            raise HTTPException(
                status_code=exc.response.status_code, detail="Failed to get user info"
            )
        username = response.json()["preferred_username"].lower()
    return create_access_token(db, username, response)


@router.get(
    "/realm-discovery/",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RealmDiscoveryResponse,
)
def get_realm(
    realm_type: str = Query(..., alias="type"),
) -> schemas.RealmDiscoveryResponse:
    """
    Discover the appropriate Keycloak realm for a realm type.

    Mobile apps should call this endpoint first to determine which realm to authenticate against.
    The response includes all necessary OIDC endpoints and configuration for the discovered realm.

    """
    if not OIDC_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="OIDC is not enabled",
        )

    try:
        normalized = schemas.RealmType(realm_type.lower().strip())
    except Exception as e:
        logger.error("Failed to discover realm of type %s: %s", realm_type, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Realm discovery failed"
        )
    # Discover realm
    try:
        realm = discover_realm(normalized)
    except Exception as e:
        logger.error("Failed to discover realm of type %s: %s", normalized, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Realm discovery failed"
        )

    response = schemas.RealmDiscoveryResponse(
        realm=realm,
        discovery_uri=f"{OIDC_BASE_URL}/realms/{realm}/.well-known/openid-configuration",
        type=normalized,
    )

    return response


def discover_realm(realm_type: schemas.RealmType) -> str:
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
