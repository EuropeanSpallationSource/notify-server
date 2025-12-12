"""
Tests for mobile API authentication with realm discovery.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import RealmType


# Test-only middleware: inject request.state.oidc_config and jwks_client so
# handlers that expect those attributes can run without needing the full
# application lifespan to execute.
from starlette.middleware.base import BaseHTTPMiddleware


class _InjectStateMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        # Build a small, predictable oidc_config mapping based on the current
        # deps.REALM_BY_TYPE. Tests mutate that mapping, so build it at request
        # time to reflect test changes.
        from app import deps
        from app.settings import OIDC_BASE_URL

        oidc = {}
        jwks = {}
        # deps.REALM_BY_TYPE maps RealmType -> realm string. Build entries for
        # both the RealmType key and the realm string so handlers can look up
        # by either.
        for realm_type, realm in deps.REALM_BY_TYPE.items():
            cfg = {
                "authorization_endpoint": f"{OIDC_BASE_URL}/realms/{realm}/protocol/openid-connect/auth",
                "token_endpoint": f"{OIDC_BASE_URL}/realms/{realm}/protocol/openid-connect/token",
                "userinfo_endpoint": f"{OIDC_BASE_URL}/realms/{realm}/protocol/openid-connect/userinfo",
                "id_token_signing_alg_values_supported": ["RS256"],
            }
            oidc[realm_type] = cfg
            jwks[realm_type] = None

        request.state.oidc_config = oidc
        request.state.jwks_client = jwks
        return await call_next(request)


@pytest.fixture(scope="module", autouse=True)
def _inject_state_middleware():
    """Add middleware to the app used by these tests. Kept module-scoped so
    middleware is added once for the test module."""
    # Import here to avoid circular imports at module import time
    from app.main import app as _original_app
    from fastapi import FastAPI

    # Create a fresh wrapper app and add the middleware to it before the
    # application is started. Mount the original app under the wrapper so the
    # wrapper's middleware runs first and injects the request.state values.
    wrapper = FastAPI(docs_url=None, redoc_url=None)
    wrapper.add_middleware(_InjectStateMiddleware)
    wrapper.mount("/", _original_app)

    # Replace the module-level `app` so tests that do `TestClient(app)` get
    # the wrapped app with our middleware.
    globals()["app"] = wrapper
    yield


@pytest.fixture(autouse=True)
def reset_realm_discovery_state():
    """Reset realm discovery module state between tests."""
    import app.api.login as login_api
    import app.deps as deps  # Store original values

    original_oidc_enabled = login_api.OIDC_ENABLED
    original_default = deps.OIDC_DEFAULT_REALM
    original_base_url = deps.OIDC_BASE_URL
    original_demo_realm = deps.OIDC_DEMO_REALM
    # store mappings built at import time so tests can mutate them safely
    original_realm_by_type = dict(deps.REALM_BY_TYPE)
    original_client_by_realm_type = dict(deps.CLIENT_BY_REALM_TYPE)

    yield  # Run the test

    # Restore original values after test
    login_api.OIDC_ENABLED = original_oidc_enabled
    deps.OIDC_DEFAULT_REALM = original_default
    deps.OIDC_BASE_URL = original_base_url
    deps.OIDC_DEMO_REALM = original_demo_realm
    deps.OIDC_DEFAULT_REALM = original_default
    deps.REALM_BY_TYPE = original_realm_by_type
    deps.CLIENT_BY_REALM_TYPE = original_client_by_realm_type


@patch("app.api.login.OIDC_ENABLED", False)
def test_realm_discovery_endpoint_oidc_disabled():
    """Test realm discovery endpoint when OIDC is disabled."""
    import app.api.login as login_api

    # Set up test configuration directly on modules
    login_api.OIDC_ENABLED = False

    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?type=real")

    assert response.status_code == 405
    assert response.json()["detail"] == "OIDC is not enabled"


@patch("app.api.login.OIDC_ENABLED", False)
def test_invalid_realm_type():
    """Test realm discovery endpoint when realm type is invalid."""
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?type=test")

    assert response.status_code == 422
    assert response.json()["detail"][0]["ctx"] == {"expected": "'real' or 'demo'"}


@pytest.mark.parametrize(
    "realm_type,demo_realm,expected_realm",
    [
        (RealmType.demo, "demo-realm", "demo-realm"),
        (RealmType.real, "demo", "default"),
        (RealmType.demo, "", "default"),
    ],
)
def test_realm_discovery_endpoint_success(realm_type, demo_realm, expected_realm):
    """Test realm discovery with various pattern matching (domain, prefix, exact)."""
    import app.api.login as login_api
    import app.deps as deps
    from app.settings import OIDC_BASE_URL

    # Set up test configuration directly on modules
    login_api.OIDC_ENABLED = True
    login_api.OIDC_DEFAULT_REALM = "default"
    deps.OIDC_DEFAULT_REALM = "default"
    deps.OIDC_DEMO_REALM = demo_realm
    # make realm mapping deterministic for the test
    deps.REALM_BY_TYPE = {
        RealmType.demo: demo_realm if demo_realm else deps.OIDC_DEFAULT_REALM,
        RealmType.real: login_api.OIDC_DEFAULT_REALM,
    }
    # set predictable client ids for assertion
    deps.CLIENT_BY_REALM_TYPE = {
        RealmType.demo: {"client_id": "demo-client"},
        RealmType.real: {"client_id": "real-client"},
    }
    expected_client_id = deps.CLIENT_BY_REALM_TYPE[realm_type]["client_id"]
    client = TestClient(app)
    response = client.get(f"/api/v1/realm-discovery/?type={realm_type.value}")

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == realm_type.value
    assert data["realm"] == expected_realm
    # Response must expose the OIDC endpoints for the discovered realm
    assert (
        data["authorization_endpoint"]
        == f"{OIDC_BASE_URL}/realms/{expected_realm}/protocol/openid-connect/auth"
    )
    assert (
        data["token_endpoint"]
        == f"{OIDC_BASE_URL}/realms/{expected_realm}/protocol/openid-connect/token"
    )
    assert data["client_id"] == expected_client_id


@pytest.mark.parametrize(
    "realm_type,expected_realm",
    [(RealmType.demo, "demo-realm"), (RealmType.real, "admin-realm")],
)
@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.deps.OIDC_DEMO_REALM", "demo")
@patch("app.api.login.OIDC_DEFAULT_REALM", "default")
def test_realm_discovery_multiple_mappings(realm_type, expected_realm):
    """Test realm discovery with multiple mapping rules."""
    import app.deps as deps

    # create explicit mapping for this test
    deps.REALM_BY_TYPE = {RealmType.demo: "demo-realm", RealmType.real: "admin-realm"}
    deps.CLIENT_BY_REALM_TYPE = {
        RealmType.demo: {"client_id": "demo-client"},
        RealmType.real: {"client_id": "real-client"},
    }
    client = TestClient(app)
    response = client.get(f"/api/v1/realm-discovery/?type={realm_type.value}")

    assert response.status_code == 200
    data = response.json()
    assert data["realm"] == expected_realm


@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.deps.OIDC_DEMO_REALM", "")
@patch("app.api.login.OIDC_DEFAULT_REALM", "master")
def test_realm_discovery_response_structure():
    """Test that response contains all required fields with correct types."""

    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?type=demo")

    assert response.status_code == 200
    data = response.json()

    # Check required fields exist
    required_fields = [
        "realm",
        "authorization_endpoint",
        "token_endpoint",
        "client_id",
        "type",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check field types
    string_fields = [
        "realm",
        "authorization_endpoint",
        "token_endpoint",
        "client_id",
        "type",
    ]
    for field in string_fields:
        assert isinstance(data[field], str), f"Field {field} should be string"

    # Check URLs are properly formatted
    url_fields = ["authorization_endpoint", "token_endpoint"]
    for field in url_fields:
        assert data[field].startswith("https://"), (
            f"Field {field} should start with https://"
        )

    # Check realm type is valid
    assert data["type"] in [e.value for e in RealmType], "Invalid realm type"


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("realm", "master"),
        ("type", "real"),
    ],
)
@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.deps.OIDC_DEMO_REALM", "")
def test_realm_discovery_response_field_values(field_name, field_value):
    """Test that response fields contain expected values."""
    import app.deps as deps
    import app.api.login as login_api

    # Ensure mapping returns master for real
    deps.REALM_BY_TYPE = {
        RealmType.real: "master",
        RealmType.demo: login_api.OIDC_DEFAULT_REALM,
    }
    deps.CLIENT_BY_REALM_TYPE = {
        RealmType.demo: {"client_id": "demo-client"},
        RealmType.real: {"client_id": "real-client"},
    }
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?type=real")

    assert response.status_code == 200
    data = response.json()
    assert data[field_name] == field_value
