"""Redis Event Publisher and Subscriber for asynchronous decoupled communication."""

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import redis.asyncio as aioredis
from pydantic import BaseModel

from shared.logging.logger import get_logger

logger = get_logger("event_bus")


class EventBus:
    """Manages publishing and subscribing to domain events via Redis."""

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.redis: aioredis.Redis | None = None
        self._handlers: dict[str, list[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]] = {}
        self._listener_task: asyncio.Task | None = None
        self._running = False
        self._memory_queue: list[dict[str, Any]] = []  # For testing fallback

    async def connect(self) -> bool:
        """Connect to Redis instance."""
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
            )
            await self.redis.ping()
            self._running = True
            logger.info("Connected to Redis Event Bus", extra={"event": "redis_connected"})
            return True
        except Exception as e:
            logger.warning(
                f"Could not connect to Redis ({e}), falling back to in-memory event bus",
                extra={"event": "redis_offline"},
            )
            self.redis = None
            self._running = True
            return False

    async def disconnect(self):
        """Disconnect and cleanup listener tasks."""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis Event Bus", extra={"event": "redis_disconnected"})

    def subscribe(
        self, event_type: str, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ):
        """Register an async handler for a given event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, channel: str, event: BaseModel | dict[str, Any]):
        """Publish an event to a Redis channel and/or local subscribers."""
        if isinstance(event, BaseModel):
            payload_dict = event.model_dump(mode="json")
        else:
            payload_dict = event

        payload_str = json.dumps(payload_dict)
        event_type = payload_dict.get("event_type", channel)

        # 1. Publish to Redis if connected
        if self.redis:
            try:
                await self.redis.publish(channel, payload_str)
                logger.info(
                    f"Published event {event_type} to channel {channel}",
                    extra={
                        "event": "event_published",
                        "extra_data": {"channel": channel, "event_type": event_type},
                    },
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish event to Redis: {e}", extra={"event": "publish_error"}
                )
        else:
            # In-memory fallback
            self._memory_queue.append(payload_dict)
            logger.info(
                f"[InMemory] Published event {event_type} to channel {channel}",
                extra={"event": "event_published_inmemory"},
            )

        # 2. Dispatch to local subscribers matching event_type or channel
        handlers = self._handlers.get(event_type, []) + self._handlers.get(channel, [])
        for handler in set(handlers):
            try:
                asyncio.create_task(handler(payload_dict))
            except Exception as e:
                logger.error(f"Error invoking event handler for {event_type}: {e}")

    async def start_listening(self, channels: list[str]):
        """Start background task listening to specified Redis channels."""
        if not self.redis:
            logger.info("Redis not connected, skipping background subscriber listener")
            return

        async def _listen():
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*channels)
            logger.info(
                f"Subscribed to Redis channels: {channels}", extra={"event": "redis_subscribed"}
            )
            try:
                while self._running:
                    try:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        )
                        if message and message.get("type") == "message":
                            data_str = message.get("data")
                            if data_str:
                                payload = json.loads(data_str)
                                event_type = payload.get("event_type", message.get("channel"))
                                handlers = self._handlers.get(event_type, []) + self._handlers.get(
                                    message.get("channel"), []
                                )
                                for handler in set(handlers):
                                    asyncio.create_task(handler(payload))
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error reading message from Redis: {e}")
                        await asyncio.sleep(1.0)
            finally:
                await pubsub.unsubscribe(*channels)
                await pubsub.close()

        self._listener_task = asyncio.create_task(_listen())
