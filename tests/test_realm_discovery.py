"""
Tests for realm discovery functionality.
"""

import pytest
from unittest.mock import patch
from app.realm_discovery import discover_realm_for_username


@pytest.mark.parametrize(
    "username,expected_realm",
    [
        ("demo", "demo-realm"),
        ("Demo", "demo-realm"),
        ("guest", "guest-realm"),
        ("anyuser", "default"),
    ],
)
@patch(
    "app.realm_discovery.OIDC_REALM_MAPPING", ["demo:demo-realm", "Guest:guest-realm"]
)
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "default")
def test_username_match(username, expected_realm):
    """Test exact username matching."""

    assert discover_realm_for_username(username) == expected_realm


@pytest.mark.parametrize(
    "username,expected_realm",
    [("demo", "default"), ("Demo", "default"), ("anyuser", "default")],
)
@patch("app.realm_discovery.OIDC_REALM_MAPPING", [])
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "default")
def test_empty_configuration(username, expected_realm):
    """Test behavior with empty realm mapping."""

    assert discover_realm_for_username(username) == expected_realm
