"""Unit tests for Serverless Azure Audit Function."""
import json
import azure.functions as func
from functions.audit_function.function_app import audit_transaction


def test_azure_audit_function_valid_request():
    payload = {
        "event_type": "PaymentCompleted",
        "order_id": "ord_audit_100",
        "payment_id": "pay_audit_100",
        "amount": 299.99,
        "currency": "USD",
    }
    req = func.HttpRequest(
        method="POST",
        body=json.dumps(payload).encode("utf-8"),
        url="/api/audit-transaction",
        headers={"Content-Type": "application/json"},
    )
    
    resp = audit_transaction(req)
    assert resp.status_code == 201
    
    body = json.loads(resp.get_body())
    assert body["status"] == "SUCCESS"
    assert body["event_type"] == "PaymentCompleted"
    assert body["order_id"] == "ord_audit_100"
    assert "audit_id" in body


def test_azure_audit_function_invalid_json():
    req = func.HttpRequest(
        method="POST",
        body=b"invalid json syntax",
        url="/api/audit-transaction",
        headers={"Content-Type": "application/json"},
    )
    
    resp = audit_transaction(req)
    assert resp.status_code == 400
    body = json.loads(resp.get_body())
    assert body["error"] == "INVALID_JSON"
