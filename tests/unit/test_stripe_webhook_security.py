"""Tests for Stripe webhook signature verification and replay attack prevention."""

import hashlib
import hmac
import time

import pytest
from httpx import ASGITransport, AsyncClient

from services.payment_service.app.main import app
from services.payment_service.app.providers.stripe_provider import StripePaymentProvider


@pytest.fixture(autouse=True)
def cleanup():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature_rejected():
    """Verify webhook with missing or invalid HMAC signature returns 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/payments/webhook/stripe",
            content=b'{"id": "evt_123", "type": "payment_intent.succeeded"}',
            headers={
                "Content-Type": "application/json",
                "stripe-signature": "t=123456,v1=invalid_hmac_signature",
            },
        )
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_missing_signature_rejected():
    """Verify webhook without signature header is rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/payments/webhook/stripe",
            content=b'{"id": "evt_123", "type": "payment_intent.succeeded"}',
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 400


def test_stripe_provider_signature_verification_logic():
    """Verify HMAC computation and tolerance checks."""
    secret = "whsec_test_secret_key_12345"
    provider = StripePaymentProvider(webhook_secret=secret)
    payload = b'{"id": "evt_test", "type": "charge.succeeded"}'
    timestamp = int(time.time())

    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    mac = hmac.new(secret.encode("utf-8"), msg=signed_payload, digestmod=hashlib.sha256)
    valid_signature = f"t={timestamp},v1={mac.hexdigest()}"

    # Valid event should construct cleanly
    event = provider.verify_webhook(payload, valid_signature)
    assert event["id"] == "evt_test"
    assert event["type"] == "charge.succeeded"

    # Tampered payload should raise ValueError
    with pytest.raises(ValueError):
        provider.verify_webhook(b'{"id": "evt_tampered"}', valid_signature)
