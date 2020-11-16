import pytest
import respx
from app import schemas, tasks


@respx.mock
@pytest.mark.asyncio
async def test_send_push_to_ios():
    apn = "apn-token"
    aps = schemas.Aps(
        alert=schemas.Alert(title="New alert", subtitle="This is a test"), badge=3
    )
    payload = schemas.ApnPayload(aps=aps)
    request = respx.post(
        f"https://api.development.push.apple.com/3/device/{apn}",
    )
    await tasks.send_push_to_ios(apn, payload)
    assert request.called
    req, _ = respx.calls[0]
    assert req.headers["apns-expiration"] == "0"
    assert req.headers["apns-priority"] == "10"
    assert req.headers["apns-topic"] == "eu.ess.ESS-Notify"
    assert req.headers["Authorization"].startswith("Bearer")
    assert req._content == payload.json().encode("utf-8")
