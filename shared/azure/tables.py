"""Azure Table Storage integration for Audit Logs and System Telemetry."""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from shared.logging.logger import get_logger

logger = get_logger("azure_tables")


class AuditTableStorage:
    """Manages audit trails and system event storage in Azure Tables or local fallback."""

    def __init__(self, table_name: str = "PaymentAuditLog", connection_string: Optional[str] = None):
        self.table_name = table_name
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.table_client = None
        self._local_audit_log: List[Dict[str, Any]] = []

        if self.connection_string and os.getenv("USE_AZURE_INTEGRATION", "false").lower() == "true":
            try:
                from azure.data.tables import TableClient

                self.table_client = TableClient.from_connection_string(
                    conn_str=self.connection_string,
                    table_name=self.table_name,
                )
                try:
                    self.table_client.create_table()
                except Exception:
                    pass  # Table likely already exists
                logger.info(f"Connected to Azure Table Storage: {self.table_name}")
            except Exception as e:
                logger.warning(f"Could not initialize Azure Table client: {e}. Using local in-memory audit log.")

    async def log_audit_event(
        self,
        partition_key: str,
        event_type: str,
        payload: Dict[str, Any],
        row_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store an immutable audit event."""
        row_id = row_key or str(uuid.uuid4())
        entity = {
            "PartitionKey": partition_key,
            "RowKey": row_id,
            "EventType": event_type,
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "Payload": json.dumps(payload),
        }

        if self.table_client:
            try:
                self.table_client.create_entity(entity=entity)
                logger.info(f"Audit record saved to Azure Tables: {partition_key}/{row_id}")
                return entity
            except Exception as e:
                logger.error(f"Failed to write to Azure Tables: {e}")

        # Local fallback
        self._local_audit_log.append(entity)
        logger.info(f"[Local Storage] Audit record saved: {partition_key}/{row_id}")
        return entity

    def get_audit_records(self, partition_key: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Query audit records."""
        if self.table_client:
            try:
                if partition_key:
                    query_filter = f"PartitionKey eq '{partition_key}'"
                    entities = list(self.table_client.query_entities(query_filter))
                else:
                    entities = list(self.table_client.list_entities())
                return entities[:limit]
            except Exception as e:
                logger.error(f"Failed to query Azure Tables: {e}")

        # Local fallback
        if partition_key:
            return [e for e in self._local_audit_log if e["PartitionKey"] == partition_key][:limit]
        return self._local_audit_log[:limit]
