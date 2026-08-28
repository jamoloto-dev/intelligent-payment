"""Unit and API tests for Order Service."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from services.order_service.app.config.settings import settings
from services.order_service.app.main import app
from services.order_service.app.repositories.order_repository import OrderRepository
from services.order_service.app.routers.order_router import get_order_service
from services.order_service.app.services.order_service import OrderService
from shared.authentication.jwt import JWTManager
from shared.database.base import Base

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


class MockProductClient:
    """Mock product client simulating stock reservation."""

    def __init__(self):
        self.inventory = {
            "prod_100": {"name": "Test Phone", "price": Decimal("500.00"), "stock": 10}
        }

    async def reserve_stock(self, product_id: str, quantity: int):
        if product_id not in self.inventory:
            raise Exception("Product not found")
        item = self.inventory[product_id]
        if item["stock"] < quantity:
            raise Exception("Insufficient stock")
        item["stock"] -= quantity
        return {
            "product_id": product_id,
            "product_name": item["name"],
            "unit_price": str(item["price"]),
            "reserved_quantity": quantity,
            "remaining_stock": item["stock"],
        }

    async def release_stock(self, product_id: str, quantity: int):
        if product_id in self.inventory:
            self.inventory[product_id]["stock"] += quantity


mock_product_client = MockProductClient()


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_order_service():
        async with TestingSessionLocal() as session:
            yield OrderService(OrderRepository(session), product_client=mock_product_client)

    app.dependency_overrides[get_order_service] = override_get_order_service
    yield
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


jwt_mgr = JWTManager(secret_key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
user_token = jwt_mgr.create_access_token(
    user_id="usr_order_test", email="order@example.com", role="USER"
)


@pytest.mark.asyncio
async def test_order_creation_and_retrieval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create order
        create_res = await ac.post(
            "/orders",
            json={
                "items": [{"product_id": "prod_100", "quantity": 2}],
                "shipping_address": "123 Main St, Tech City",
                "currency": "USD",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert create_res.status_code == 201
        order_data = create_res.json()
        assert order_data["user_id"] == "usr_order_test"
        assert float(order_data["total_amount"]) == 1000.00
        assert order_data["status"] == "PENDING"
        assert len(order_data["items"]) == 1
        assert order_data["items"][0]["quantity"] == 2

        order_id = order_data["id"]

        # Retrieve order
        get_res = await ac.get(
            f"/orders/{order_id}", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert get_res.status_code == 200
        assert get_res.json()["id"] == order_id


@pytest.mark.asyncio
async def test_order_cancellation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(
            "/orders",
            json={
                "items": [{"product_id": "prod_100", "quantity": 1}],
                "shipping_address": "456 Market St",
                "currency": "USD",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        order_id = create_res.json()["id"]

        # Cancel order
        cancel_res = await ac.post(
            f"/orders/{order_id}/cancel", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"
