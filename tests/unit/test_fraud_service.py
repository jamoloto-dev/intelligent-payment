"""Unit and API tests for Fraud Detection Service."""

import pytest
from httpx import ASGITransport, AsyncClient

from services.fraud_service.app.main import app
from services.fraud_service.app.rules.rules import (
    GeolocationMismatchRule,
    HighAmountRule,
    VelocityRule,
)
from services.fraud_service.app.schemas.fraud import FraudCheckRequest


def test_fraud_high_amount_rule():
    rule = HighAmountRule(high_threshold=1000.0, critical_threshold=5000.0)

    # Low amount
    low_req = FraudCheckRequest(
        transaction_id="tx_1", order_id="ord_1", user_id="usr_1", amount=150.0
    )
    res_low = rule.evaluate(low_req)
    assert not res_low.triggered
    assert res_low.score_increment == 0.0

    # High amount
    high_req = FraudCheckRequest(
        transaction_id="tx_2", order_id="ord_2", user_id="usr_2", amount=1500.0
    )
    res_high = rule.evaluate(high_req)
    assert res_high.triggered
    assert res_high.score_increment == 25.0

    # Critical amount
    crit_req = FraudCheckRequest(
        transaction_id="tx_3", order_id="ord_3", user_id="usr_3", amount=6500.0
    )
    res_crit = rule.evaluate(crit_req)
    assert res_crit.triggered
    assert res_crit.score_increment == 45.0


def test_fraud_velocity_rule():
    rule = VelocityRule(max_hourly_velocity=5)

    req_burst = FraudCheckRequest(
        transaction_id="tx_v",
        order_id="ord_v",
        user_id="usr_v",
        amount=50.0,
        recent_transactions_count_1h=6,
    )
    res = rule.evaluate(req_burst)
    assert res.triggered
    assert res.score_increment == 35.0


def test_fraud_geolocation_mismatch():
    rule = GeolocationMismatchRule()

    req_mismatch = FraudCheckRequest(
        transaction_id="tx_geo",
        order_id="ord_geo",
        user_id="usr_geo",
        amount=100.0,
        billing_country="US",
        ip_country="NG",
    )
    res = rule.evaluate(req_mismatch)
    assert res.triggered
    assert res.score_increment == 25.0


@pytest.mark.asyncio
async def test_fraud_api_evaluation_and_decision():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Clean transaction -> APPROVE
        clean_res = await ac.post(
            "/fraud/check",
            json={
                "transaction_id": "tx_clean_100",
                "order_id": "ord_100",
                "user_id": "usr_100",
                "amount": 49.99,
                "currency": "USD",
                "recent_transactions_count_1h": 0,
                "recent_failed_payments_24h": 0,
            },
        )
        assert clean_res.status_code == 200
        clean_data = clean_res.json()
        assert clean_data["decision"] == "APPROVE"
        assert clean_data["risk_level"] == "LOW"
        assert clean_data["risk_score"] == 0.0

        # 2. Critical Fraud Transaction -> REJECT
        fraud_res = await ac.post(
            "/fraud/check",
            json={
                "transaction_id": "tx_fraud_999",
                "order_id": "ord_999",
                "user_id": "usr_999",
                "amount": 7500.00,
                "currency": "USD",
                "recent_transactions_count_1h": 8,
                "recent_failed_payments_24h": 4,
                "billing_country": "US",
                "ip_country": "RU",
            },
        )
        assert fraud_res.status_code == 200
        fraud_data = fraud_res.json()
        assert fraud_data["decision"] == "REJECT"
        assert fraud_data["risk_level"] == "CRITICAL"
        assert fraud_data["risk_score"] >= 80.0
        assert len(fraud_data["reasons"]) >= 3

        # 3. Retrieve evaluation by transaction_id
        get_res = await ac.get("/fraud/tx_fraud_999")
        assert get_res.status_code == 200
        assert get_res.json()["decision"] == "REJECT"
