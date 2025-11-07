"""
Tests for mobile API authentication with realm discovery.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import RealmType


@pytest.fixture(autouse=True)
def reset_realm_discovery_state():
    """Reset realm discovery module state between tests."""
    import app.realm_discovery as rd
    import app.api.login as login_api

    # Store original values
    original_mapping = rd.OIDC_REALM_MAPPING
    original_default = rd.OIDC_DEFAULT_REALM
    original_base_url = rd.OIDC_BASE_URL
    original_client_id = rd.OIDC_CLIENT_ID
    original_scope = rd.OIDC_SCOPE
    original_oidc_enabled = login_api.OIDC_ENABLED

    yield  # Run the test

    # Clear any discovery cache
    login_api._DISCOVERY_CACHE.clear()

    # Restore original values after test
    rd.OIDC_REALM_MAPPING = original_mapping
    rd.OIDC_DEFAULT_REALM = original_default
    rd.OIDC_BASE_URL = original_base_url
    rd.OIDC_CLIENT_ID = original_client_id
    rd.OIDC_SCOPE = original_scope
    login_api.OIDC_ENABLED = original_oidc_enabled


@patch("app.api.login.OIDC_ENABLED", False)
def test_realm_discovery_endpoint_oidc_disabled():
    """Test realm discovery endpoint when OIDC is disabled."""
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?username=testuser")

    assert response.status_code == 503
    assert response.json() == {"detail": "OIDC is not enabled"}


@pytest.mark.parametrize(
    "username,realm_mapping,expected_realm",
    [
        ("demo", ["demo:demo-realm"], "demo-realm"),
        ("unknown", ["demo:demo-realm"], "default"),
        ("demo", [], "default"),
    ],
)
def test_realm_discovery_endpoint_success(username, realm_mapping, expected_realm):
    """Test realm discovery with various pattern matching (domain, prefix, exact)."""
    import app.realm_discovery as rd
    import app.api.login as login_api

    # Set up test configuration directly on modules
    login_api.OIDC_ENABLED = True
    rd.OIDC_BASE_URL = "https://keycloak.test.com/auth"
    rd.OIDC_CLIENT_ID = "test-client"
    rd.OIDC_SCOPE = "openid profile email"
    rd.OIDC_DEFAULT_REALM = "default"
    rd.OIDC_REALM_MAPPING = realm_mapping

    client = TestClient(app)
    response = client.get(f"/api/v1/realm-discovery/?username={username}")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert data["realm"] == expected_realm
    assert data["issuer"] == f"https://keycloak.test.com/auth/realms/{expected_realm}"
    assert (
        data["authorization_endpoint"]
        == f"https://keycloak.test.com/auth/realms/{expected_realm}/protocol/openid-connect/auth"
    )
    assert (
        data["token_endpoint"]
        == f"https://keycloak.test.com/auth/realms/{expected_realm}/protocol/openid-connect/token"
    )
    assert data["client_id"] == "test-client"
    assert data["scope"] == "openid profile email"
    assert data["type"] == "real"


@pytest.mark.parametrize(
    "username,expected_realm",
    [("demo", "demo-realm"), ("admin", "admin-realm"), ("unknown_user", "default")],
)
@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.realm_discovery.OIDC_BASE_URL", "https://keycloak.test.com/auth")
@patch("app.realm_discovery.OIDC_CLIENT_ID", "test-client")
@patch("app.realm_discovery.OIDC_SCOPE", "openid profile email")
@patch(
    "app.realm_discovery.OIDC_REALM_MAPPING", ["demo:demo-realm", "admin:admin-realm"]
)
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "default")
def test_realm_discovery_multiple_mappings(username, expected_realm):
    """Test realm discovery with multiple mapping rules."""
    client = TestClient(app)
    response = client.get(f"/api/v1/realm-discovery/?username={username}")

    assert response.status_code == 200
    data = response.json()
    assert data["realm"] == expected_realm


@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.realm_discovery.OIDC_BASE_URL", "https://keycloak.test.com/auth")
@patch("app.realm_discovery.OIDC_CLIENT_ID", "test-client")
@patch("app.realm_discovery.OIDC_SCOPE", "openid profile email")
@patch("app.realm_discovery.OIDC_REALM_MAPPING", [])
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "master")
def test_realm_discovery_response_structure():
    """Test that response contains all required fields with correct types."""
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?username=testuser")

    assert response.status_code == 200
    data = response.json()

    # Check required fields exist
    required_fields = [
        "username",
        "realm",
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "client_id",
        "scope",
        "type",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check field types
    string_fields = [
        "username",
        "realm",
        "issuer",
        "authorization_endpoint",
        "token_endpoint",
        "client_id",
        "scope",
        "type",
    ]
    for field in string_fields:
        assert isinstance(data[field], str), f"Field {field} should be string"

    # Check URLs are properly formatted
    url_fields = ["issuer", "authorization_endpoint", "token_endpoint"]
    for field in url_fields:
        assert data[field].startswith("https://"), (
            f"Field {field} should start with https://"
        )

    # Check realm type is valid
    assert data["type"] in [e.value for e in RealmType], "Invalid realm type"


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        ("username", "testuser"),
        ("realm", "master"),
        ("client_id", "test-client"),
        ("scope", "openid profile email"),
        ("type", "real"),
    ],
)
@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.realm_discovery.OIDC_BASE_URL", "https://keycloak.test.com/auth")
@patch("app.realm_discovery.OIDC_CLIENT_ID", "test-client")
@patch("app.realm_discovery.OIDC_SCOPE", "openid profile email")
@patch("app.realm_discovery.OIDC_REALM_MAPPING", [])
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "master")
def test_realm_discovery_response_field_values(field_name, field_value):
    """Test that response fields contain expected values."""
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?username=testuser")

    assert response.status_code == 200
    data = response.json()
    assert data[field_name] == field_value
