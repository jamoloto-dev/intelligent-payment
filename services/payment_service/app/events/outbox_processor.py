"""Transactional Outbox background processor for reliable event dispatch."""

import asyncio
import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.payment_service.app.repositories.payment_repository import PaymentRepository
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger

logger = get_logger("outbox-processor")


class OutboxProcessor:
    """Dispatches persisted outbox messages to Redis EventBus with guaranteed delivery."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], event_bus: EventBus):
        self.session_factory = session_factory
        self.event_bus = event_bus
        self._running = False
        self._task: asyncio.Task | None = None

    async def process_batch(self, limit: int = 50) -> int:
        """Process a single batch of pending outbox messages."""
        async with self.session_factory() as session:
            repo = PaymentRepository(session)
            pending_messages = await repo.get_pending_outbox_messages(limit=limit)
            if not pending_messages:
                return 0

            dispatched_count = 0
            for msg in pending_messages:
                try:
                    payload_data = (
                        json.loads(msg.payload) if isinstance(msg.payload, str) else msg.payload
                    )
                    # Publish to EventBus
                    await self.event_bus.publish(msg.topic, payload_data)
                    await repo.mark_outbox_published(msg.id)
                    dispatched_count += 1
                    logger.info(
                        f"Outbox event {msg.id} ({msg.event_type}) published to topic '{msg.topic}'"
                    )
                except Exception as e:
                    logger.error(f"Failed to publish outbox event {msg.id}: {e}")
                    await repo.mark_outbox_failed(msg.id, str(e))

            return dispatched_count

    async def start(self, poll_interval_seconds: float = 2.0):
        """Start the background worker loop."""
        self._running = True
        logger.info("OutboxProcessor background worker started.")
        while self._running:
            try:
                await self.process_batch()
            except Exception as e:
                logger.error(f"Error in outbox processing cycle: {e}")
            await asyncio.sleep(poll_interval_seconds)

    def stop(self):
        """Stop the background worker loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("OutboxProcessor background worker stopped.")
