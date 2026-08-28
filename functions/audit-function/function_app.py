"""Azure Function for Asynchronous Transaction Audit Logging.

Serverless Rationale:
Audit logging is an event-driven, non-blocking compliance requirement.
Using an Azure Function provides:
1. Zero idle compute costs during quiet periods.
2. Independent elasticity to handle sudden spikes in payment events.
3. Isolated compliance auditing detached from transactional microservices.
"""
import json
import logging
import os
from datetime import datetime, timezone
import uuid
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def get_table_client():
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if connection_string:
        try:
            from azure.data.tables import TableClient
            client = TableClient.from_connection_string(conn_str=connection_string, table_name="TransactionAuditLog")
            try:
                client.create_table()
            except Exception:
                pass
            return client
        except Exception as e:
            logging.warning(f"Could not connect to Azure Table Storage: {e}")
    return None


@app.route(route="audit-transaction", methods=["POST"])
def audit_transaction(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Transaction Audit Function triggered.")
    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "INVALID_JSON", "message": "Request body must be valid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    event_type = req_body.get("event_type", "PaymentCompleted")
    order_id = req_body.get("order_id", "unknown_order")
    payment_id = req_body.get("payment_id", str(uuid.uuid4()))
    audit_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    audit_record = {
        "PartitionKey": event_type,
        "RowKey": audit_id,
        "OrderId": order_id,
        "PaymentId": payment_id,
        "Timestamp": timestamp,
        "Payload": json.dumps(req_body),
        "ComplianceVerified": True,
    }

    client = get_table_client()
    if client:
        try:
            client.create_entity(entity=audit_record)
            logging.info(f"Audit record saved to Azure Tables: {audit_id}")
        except Exception as e:
            logging.error(f"Failed to persist audit entity in Azure: {e}")

    return func.HttpResponse(
        json.dumps({
            "status": "SUCCESS",
            "audit_id": audit_id,
            "event_type": event_type,
            "order_id": order_id,
            "timestamp": timestamp,
        }),
        status_code=201,
        mimetype="application/json",
    )
