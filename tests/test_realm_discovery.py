"""
Tests for realm discovery functionality.
"""

import pytest
from unittest.mock import patch
from app.realm_discovery import discover_realm


@pytest.mark.parametrize(
    "realm_type,expected_realm",
    [
        ("demo", "demo-realm"),
        ("Demo", "demo-realm"),
        ("real", "real-realm"),
        ("unknown", "default"),
    ],
)
@patch("app.realm_discovery.OIDC_REALM_MAPPING", ["demo:demo-realm", "real:real-realm"])
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "default")
def test_username_match(realm_type, expected_realm):
    """Test exact username matching."""

    assert discover_realm(realm_type) == expected_realm


@pytest.mark.parametrize(
    "realm_type,expected_realm",
    [(" ", "default"), ("", "default"), ("Unknown", "default")],
)
@patch("app.realm_discovery.OIDC_REALM_MAPPING", [])
@patch("app.realm_discovery.OIDC_DEFAULT_REALM", "default")
def test_empty_configuration(realm_type, expected_realm):
    """Test behavior with empty realm mapping."""

    assert discover_realm(realm_type) == expected_realm
