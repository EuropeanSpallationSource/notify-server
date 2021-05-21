import httpx
import pytest
import respx
from app import auth


@respx.mock
@pytest.mark.parametrize(
    "side_effect, expected",
    [
        (httpx.Response(200), True),
        (httpx.Response(201), True),
        (httpx.ConnectError, False),
        (httpx.ConnectTimeout, False),
        (httpx.Response(400), False),
        (httpx.Response(403), False),
        (httpx.Response(405), False),
        (httpx.Response(500), False),
        (httpx.Response(429), False),
    ],
)
def test_url_authenticate_user(side_effect, expected):
    request = respx.post(
        "https://auth.example.org/login",
    )
    request.side_effect = side_effect
    result = auth.url_authenticate_user("john", "secret")
    assert request.called
    assert result is expected
