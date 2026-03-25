"""
Tests for the OIDC refresh token endpoint and updated open_id_connect response.
"""

import httpx
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.main import app as original_app
from app import models, utils


# Reuse the middleware injection pattern from test_login_realm_discovery.py
# but provide a real mock jwks_client for refresh tests.


class _InjectStateMiddleware(BaseHTTPMiddleware):
    """Inject request.state.oidc_config and jwks_client for tests."""

    def __init__(self, app, jwks_client_factory=None):
        super().__init__(app)
        self.jwks_client_factory = jwks_client_factory

    async def dispatch(self, request, call_next):
        from app import deps
        from app.settings import OIDC_BASE_URL

        oidc = {}
        jwks = {}
        for realm_type, realm in deps.REALM_BY_TYPE.items():
            cfg = {
                "authorization_endpoint": f"{OIDC_BASE_URL}/realms/{realm}/protocol/openid-connect/auth",
                "token_endpoint": f"{OIDC_BASE_URL}/realms/{realm}/protocol/openid-connect/token",
                "userinfo_endpoint": f"{OIDC_BASE_URL}/realms/{realm}/protocol/openid-connect/userinfo",
                "id_token_signing_alg_values_supported": ["RS256"],
            }
            oidc[realm_type] = cfg
            jwks[realm_type] = (
                self.jwks_client_factory() if self.jwks_client_factory else None
            )

        request.state.oidc_config = oidc
        request.state.jwks_client = jwks
        return await call_next(request)


def _make_mock_jwks_client():
    mock = MagicMock()
    mock_key = MagicMock()
    mock_key.key = "test-key"
    mock.get_signing_key_from_jwt.return_value = mock_key
    return mock


wrapper = FastAPI(docs_url=None, redoc_url=None)
wrapper.add_middleware(
    _InjectStateMiddleware, jwks_client_factory=_make_mock_jwks_client
)
wrapper.mount("/", original_app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset module state between tests."""
    import app.deps as deps

    original_realm_by_type = dict(deps.REALM_BY_TYPE)
    original_client_by_realm_type = dict(deps.CLIENT_BY_REALM_TYPE)

    yield

    deps.REALM_BY_TYPE = original_realm_by_type
    deps.CLIENT_BY_REALM_TYPE = original_client_by_realm_type


@pytest.fixture
def test_client():
    with TestClient(wrapper) as c:
        yield c


# --- Tests for updated /open_id_connect response ---


def test_open_id_connect_returns_refresh_token(test_client, db, mocker):
    """open_id_connect should return refresh_token and expires_in."""
    keycloak_token_response = {
        "access_token": "kc-access-token",
        "id_token": "kc-id-token",
        "refresh_token": "kc-refresh-token",
    }
    keycloak_userinfo_response = {"preferred_username": "TestUser"}

    mocker.patch("app.api.login.utils.validate_id_token")

    mock_post = mocker.patch("httpx.AsyncClient.post")
    # First call: token endpoint, second call: userinfo endpoint
    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = keycloak_token_response
    mock_token_resp.raise_for_status = MagicMock()

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.json.return_value = keycloak_userinfo_response
    mock_userinfo_resp.raise_for_status = MagicMock()

    mock_post.side_effect = [mock_token_resp, mock_userinfo_resp]

    response = test_client.post(
        "/api/v1/open_id_connect",
        json={
            "code": "auth-code",
            "code_verifier": "verifier",
            "client_id": "notify",
            "redirect_uri": "app://callback",
            "realm": "real",
        },
    )

    assert response.status_code == 201  # new user created
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["refresh_token"] == "kc-refresh-token"
    assert data["expires_in"] > 0
    # Verify the user was created
    assert utils.decode_access_token(data["access_token"])["sub"] == "testuser"


def test_open_id_connect_without_refresh_token(test_client, db, mocker):
    """When Keycloak doesn't return a refresh_token, the field should be absent."""
    keycloak_token_response = {
        "access_token": "kc-access-token",
        "id_token": "kc-id-token",
        # No refresh_token
    }
    keycloak_userinfo_response = {"preferred_username": "NoRefreshUser"}

    mocker.patch("app.api.login.utils.validate_id_token")

    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = keycloak_token_response
    mock_token_resp.raise_for_status = MagicMock()

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.json.return_value = keycloak_userinfo_response
    mock_userinfo_resp.raise_for_status = MagicMock()

    mock_post.side_effect = [mock_token_resp, mock_userinfo_resp]

    response = test_client.post(
        "/api/v1/open_id_connect",
        json={
            "code": "auth-code",
            "code_verifier": "verifier",
            "client_id": "notify",
            "redirect_uri": "app://callback",
            "realm": "real",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" not in data


# --- Tests for /refresh endpoint ---


def test_refresh_success(test_client, db, user, mocker):
    """Successful refresh should return new tokens and update login expiry."""
    assert not user.is_logged_in

    keycloak_token_response = {
        "access_token": "new-kc-access-token",
        "id_token": "new-kc-id-token",
        "refresh_token": "new-kc-refresh-token",
    }

    mocker.patch("app.api.login.utils.validate_id_token")
    mocker.patch(
        "app.api.login.jwt.decode",
        return_value={"preferred_username": user.username},
    )

    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_resp = MagicMock()
    mock_resp.json.return_value = keycloak_token_response
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    response = test_client.post(
        "/api/v1/refresh",
        json={"refresh_token": "old-kc-refresh-token", "realm": "real"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["refresh_token"] == "new-kc-refresh-token"
    assert data["expires_in"] > 0
    # Verify the token is valid by decoding it (mock is scoped to this test)
    mocker.stopall()
    assert utils.decode_access_token(data["access_token"])["sub"] == user.username
    assert user.is_logged_in


def test_refresh_creates_new_user(test_client, db, mocker):
    """Refresh with an unknown username should create a new user."""
    keycloak_token_response = {
        "access_token": "new-kc-access-token",
        "id_token": "new-kc-id-token",
        "refresh_token": "new-kc-refresh-token",
    }

    mocker.patch("app.api.login.utils.validate_id_token")
    mocker.patch(
        "app.api.login.jwt.decode",
        return_value={"preferred_username": "BrandNewUser"},
    )

    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_resp = MagicMock()
    mock_resp.json.return_value = keycloak_token_response
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    response = test_client.post(
        "/api/v1/refresh",
        json={"refresh_token": "some-refresh-token", "realm": "real"},
    )

    assert response.status_code == 201
    data = response.json()
    mocker.stopall()
    assert utils.decode_access_token(data["access_token"])["sub"] == "brandnewuser"
    db_user = (
        db.query(models.User).filter(models.User.username == "brandnewuser").first()
    )
    assert db_user is not None


def test_refresh_invalid_token(test_client, db, mocker):
    """Keycloak rejecting the refresh token should return 401."""
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request", request=MagicMock(), response=MagicMock(status_code=400)
    )
    mock_resp.content = b"invalid_grant"
    mock_post.return_value = mock_resp

    response = test_client.post(
        "/api/v1/refresh",
        json={"refresh_token": "bad-token", "realm": "real"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token is invalid or expired"


def test_refresh_keycloak_unreachable(test_client, db, mocker):
    """Network error contacting Keycloak should return 401."""
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_post.side_effect = httpx.RequestError(
        "Connection refused", request=MagicMock()
    )

    response = test_client.post(
        "/api/v1/refresh",
        json={"refresh_token": "some-token", "realm": "real"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Failed to refresh token"


def test_refresh_id_token_validation_fails(test_client, db, mocker):
    """If id_token validation fails during refresh, return 401."""
    keycloak_token_response = {
        "access_token": "new-kc-access-token",
        "id_token": "new-kc-id-token",
        "refresh_token": "new-kc-refresh-token",
    }

    mocker.patch(
        "app.api.login.utils.validate_id_token",
        side_effect=ValueError("bad token"),
    )

    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_resp = MagicMock()
    mock_resp.json.return_value = keycloak_token_response
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    response = test_client.post(
        "/api/v1/refresh",
        json={"refresh_token": "some-token", "realm": "real"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "id_token validation failed"
