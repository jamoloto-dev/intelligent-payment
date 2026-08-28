"""Unit and API tests for Product Service."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from shared.authentication.jwt import JWTManager
from shared.database.base import Base
from services.product_service.app.config.settings import settings
from services.product_service.app.main import app
from services.product_service.app.repositories.product_repository import ProductRepository
from services.product_service.app.routers.product_router import get_product_service
from services.product_service.app.services.product_service import ProductService

# In-memory test DB
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_product_service():
    async with TestingSessionLocal() as session:
        yield ProductService(ProductRepository(session))


app.dependency_overrides[get_product_service] = override_get_product_service

jwt_mgr = JWTManager(secret_key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
admin_token = jwt_mgr.create_access_token(user_id="admin_1", email="admin@example.com", role="ADMIN")
user_token = jwt_mgr.create_access_token(user_id="user_1", email="user@example.com", role="USER")


@pytest.mark.asyncio
async def test_create_and_get_product():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Non-admin forbidden
        forbidden_res = await ac.post(
            "/products",
            json={"name": "Laptop", "price": 999.99, "stock_quantity": 10},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert forbidden_res.status_code == 403

        # Admin created
        res = await ac.post(
            "/products",
            json={"name": "MacBook Pro", "description": "M3 Chip", "price": 1999.99, "stock_quantity": 5},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 201
        prod_data = res.json()
        assert prod_data["name"] == "MacBook Pro"
        assert float(prod_data["price"]) == 1999.99
        assert prod_data["stock_quantity"] == 5

        # Get product
        get_res = await ac.get(f"/products/{prod_data['id']}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "MacBook Pro"


@pytest.mark.asyncio
async def test_reserve_and_release_stock():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create product with 10 units
        create_res = await ac.post(
            "/products",
            json={"name": "Wireless Mouse", "price": 29.99, "stock_quantity": 10},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        prod_id = create_res.json()["id"]

        # Reserve 4 units
        reserve_res = await ac.post(f"/products/{prod_id}/reserve", json={"quantity": 4})
        assert reserve_res.status_code == 200
        assert reserve_res.json()["remaining_stock"] == 6

        # Reserve another 7 units (should fail due to insufficient stock)
        fail_reserve = await ac.post(f"/products/{prod_id}/reserve", json={"quantity": 7})
        assert fail_reserve.status_code == 400
        assert fail_reserve.json()["error"] == "INSUFFICIENT_STOCK"

        # Release 2 units back
        release_res = await ac.post(f"/products/{prod_id}/release", json={"quantity": 2})
        assert release_res.status_code == 200
        assert release_res.json()["remaining_stock"] == 8
