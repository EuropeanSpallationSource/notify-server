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
    import app.api.login as login_api

    # Store original values
    original_mapping = login_api.OIDC_REALM_MAPPING
    original_default = login_api.OIDC_DEFAULT_REALM
    original_base_url = login_api.OIDC_BASE_URL
    original_oidc_enabled = login_api.OIDC_ENABLED

    yield  # Run the test

    # Restore original values after test
    login_api.OIDC_REALM_MAPPING = original_mapping
    login_api.OIDC_DEFAULT_REALM = original_default
    login_api.OIDC_BASE_URL = original_base_url
    login_api.OIDC_ENABLED = original_oidc_enabled


@patch("app.api.login.OIDC_ENABLED", False)
def test_realm_discovery_endpoint_oidc_disabled():
    """Test realm discovery endpoint when OIDC is disabled."""
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?type=test")

    assert response.status_code == 422
    assert response.json()["detail"][0]["ctx"] == {"expected": "'real' or 'demo'"}


@pytest.mark.parametrize(
    "realm_type,realm_mapping,expected_realm",
    [
        ("demo", ["demo:demo-realm"], "demo-realm"),
        ("real", ["demo:demo-realm"], "default"),
        ("demo", [], "default"),
    ],
)
def test_realm_discovery_endpoint_success(realm_type, realm_mapping, expected_realm):
    """Test realm discovery with various pattern matching (domain, prefix, exact)."""
    import app.api.login as login_api

    # Set up test configuration directly on modules
    login_api.OIDC_ENABLED = True
    login_api.OIDC_BASE_URL = "https://keycloak.test.com/auth"
    login_api.OIDC_DEFAULT_REALM = "default"
    login_api.OIDC_REALM_MAPPING = realm_mapping
    client = TestClient(app)
    response = client.get(f"/api/v1/realm-discovery/?type={realm_type}")

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == realm_type
    assert data["realm"] == expected_realm
    assert (
        data["discovery_uri"]
        == f"https://keycloak.test.com/auth/realms/{expected_realm}"
    )


@pytest.mark.parametrize(
    "realm_type,expected_realm",
    [("demo", "demo-realm"), ("real", "admin-realm")],
)
@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.api.login.OIDC_BASE_URL", "https://keycloak.test.com/auth")
@patch("app.api.login.OIDC_REALM_MAPPING", ["demo:demo-realm", "real:admin-realm"])
@patch("app.api.login.OIDC_DEFAULT_REALM", "default")
def test_realm_discovery_multiple_mappings(realm_type, expected_realm):
    """Test realm discovery with multiple mapping rules."""
    client = TestClient(app)
    response = client.get(f"/api/v1/realm-discovery/?type={realm_type}")

    assert response.status_code == 200
    data = response.json()
    assert data["realm"] == expected_realm


@patch("app.api.login.OIDC_ENABLED", True)
@patch("app.api.login.OIDC_BASE_URL", "https://keycloak.test.com/auth")
@patch("app.api.login.OIDC_REALM_MAPPING", [])
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
        "discovery_uri",
        "type",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Check field types
    string_fields = [
        "realm",
        "discovery_uri",
        "type",
    ]
    for field in string_fields:
        assert isinstance(data[field], str), f"Field {field} should be string"

    # Check URLs are properly formatted
    url_fields = ["discovery_uri"]
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
@patch("app.api.login.OIDC_BASE_URL", "https://keycloak.test.com/auth")
@patch("app.api.login.OIDC_REALM_MAPPING", [])
@patch("app.api.login.OIDC_DEFAULT_REALM", "master")
def test_realm_discovery_response_field_values(field_name, field_value):
    """Test that response fields contain expected values."""
    client = TestClient(app)
    response = client.get("/api/v1/realm-discovery/?type=real")

    assert response.status_code == 200
    data = response.json()
    assert data[field_name] == field_value
