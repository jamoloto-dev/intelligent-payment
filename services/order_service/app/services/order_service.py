"""Order service business logic layer."""

from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, status

from services.order_service.app.config.settings import settings
from services.order_service.app.models.order import Order, OrderItem
from services.order_service.app.repositories.order_repository import OrderRepository
from services.order_service.app.schemas.order import (
    OrderCreateRequest,
    OrderResponse,
    OrderUpdateRequest,
)
from shared.events.redis_client import EventBus
from shared.logging.logger import get_logger
from shared.schemas.common import OrderStatus
from shared.schemas.events import OrderCancelledEvent, OrderCreatedEvent, OrderItemPayload

logger = get_logger("order-service")


class OrderService:
    """Handles order creation, inventory reservation coordination, and lifecycle."""

    def __init__(
        self,
        repository: OrderRepository,
        event_bus: EventBus | None = None,
        product_client: Any | None = None,
    ):
        self.repository = repository
        self.event_bus = event_bus
        self.product_client = product_client

    async def _reserve_product(self, product_id: str, quantity: int) -> dict[str, Any]:
        """Call Product Service to atomically reserve stock."""
        if self.product_client:
            # Custom or mocked client
            return await self.product_client.reserve_stock(product_id, quantity)

        url = f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}/reserve"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.post(url, json={"quantity": quantity})
                if resp.status_code != 200:
                    error_data = (
                        resp.json()
                        if resp.headers.get("content-type") == "application/json"
                        else {}
                    )
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail={
                            "error": error_data.get("error", "INVENTORY_ERROR"),
                            "message": error_data.get(
                                "message", f"Failed to reserve product {product_id}"
                            ),
                        },
                    )
                return resp.json()
            except httpx.RequestError as e:
                logger.error(f"Failed to communicate with Product Service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": "PRODUCT_SERVICE_UNAVAILABLE",
                        "message": "Product Service is currently unreachable",
                    },
                )

    async def _release_product(self, product_id: str, quantity: int) -> None:
        """Call Product Service to release previously reserved stock."""
        if self.product_client:
            await self.product_client.release_stock(product_id, quantity)
            return

        url = f"{settings.PRODUCT_SERVICE_URL}/products/{product_id}/release"
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(url, json={"quantity": quantity})
            except Exception as e:
                logger.error(f"Failed to release product stock for {product_id}: {e}")

    async def create_order(
        self, user_id: str, user_email: str | None, req: OrderCreateRequest
    ) -> OrderResponse:
        reserved_items = []
        total_amount = Decimal("0.00")

        # 1. Reserve stock for each item
        try:
            for item_req in req.items:
                res = await self._reserve_product(item_req.product_id, item_req.quantity)
                unit_price = Decimal(str(res.get("unit_price", "0.00")))
                subtotal = unit_price * item_req.quantity
                total_amount += subtotal
                reserved_items.append(
                    {
                        "product_id": item_req.product_id,
                        "product_name": res.get("product_name", f"Product {item_req.product_id}"),
                        "quantity": item_req.quantity,
                        "unit_price": unit_price,
                        "subtotal": subtotal,
                    }
                )
        except Exception as exc:
            # Compensating transaction: release all already-reserved items
            for item in reserved_items:
                await self._release_product(item["product_id"], item["quantity"])
            raise exc

        # 2. Persist Order and Items
        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING.value,
            total_amount=total_amount,
            currency=req.currency or "USD",
            shipping_address=req.shipping_address,
        )
        for item_data in reserved_items:
            order_item = OrderItem(
                product_id=item_data["product_id"],
                product_name=item_data["product_name"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                subtotal=item_data["subtotal"],
            )
            order.items.append(order_item)

        created_order = await self.repository.create(order)
        logger.info(
            f"Created order: {created_order.id} for user {user_id} with total {total_amount}"
        )

        # 3. Publish OrderCreated event
        if self.event_bus:
            event = OrderCreatedEvent(
                order_id=created_order.id,
                user_id=user_id,
                total_amount=total_amount,
                currency=created_order.currency,
                user_email=user_email,
                items=[
                    OrderItemPayload(
                        product_id=i.product_id,
                        product_name=i.product_name,
                        quantity=i.quantity,
                        unit_price=i.unit_price,
                        subtotal=i.subtotal,
                    )
                    for i in created_order.items
                ],
            )
            await self.event_bus.publish("orders", event)

        return OrderResponse.model_validate(created_order)

    async def get_order(self, order_id: str) -> OrderResponse:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ORDER_NOT_FOUND", "message": f"Order {order_id} not found"},
            )
        return OrderResponse.model_validate(order)

    async def update_order(self, order_id: str, req: OrderUpdateRequest) -> OrderResponse:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ORDER_NOT_FOUND", "message": f"Order {order_id} not found"},
            )
        if req.shipping_address is not None:
            order.shipping_address = req.shipping_address
        if req.status is not None:
            order.status = req.status.value

        updated = await self.repository.update(order)
        return OrderResponse.model_validate(updated)

    async def cancel_order(
        self, order_id: str, user_id: str, is_admin: bool = False, reason: str | None = None
    ) -> OrderResponse:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ORDER_NOT_FOUND", "message": f"Order {order_id} not found"},
            )
        if not is_admin and order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "FORBIDDEN", "message": "Access denied to cancel this order"},
            )
        if order.status in [OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_ORDER_STATE",
                    "message": f"Order is already {order.status}",
                },
            )

        order.status = OrderStatus.CANCELLED.value
        updated = await self.repository.update(order)

        # Release stock
        for item in order.items:
            await self._release_product(item.product_id, item.quantity)

        # Publish cancellation event
        if self.event_bus:
            event = OrderCancelledEvent(order_id=order.id, user_id=order.user_id, reason=reason)
            await self.event_bus.publish("orders", event)

        logger.info(f"Order {order_id} was successfully cancelled")
        return OrderResponse.model_validate(updated)

    async def update_status(
        self, order_id: str, new_status: OrderStatus, reason: str | None = None
    ) -> OrderResponse:
        order = await self.repository.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ORDER_NOT_FOUND", "message": f"Order {order_id} not found"},
            )
        order.status = new_status.value
        updated = await self.repository.update(order)
        logger.info(f"Order {order_id} status updated to {new_status.value}")
        return OrderResponse.model_validate(updated)

    async def list_orders(
        self,
        user_id: str | None = None,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OrderResponse], int]:
        orders, total = await self.repository.list_orders(
            user_id=user_id, status=status_filter, page=page, page_size=page_size
        )
        return [OrderResponse.model_validate(o) for o in orders], total
