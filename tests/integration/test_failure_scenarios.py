"""Integration tests for failure scenarios, edge cases, and security boundaries."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import services.order_service.app.main as order_main
import services.payment_service.app.main as payment_main
import services.product_service.app.main as product_main
import services.user_service.app.main as user_main
from shared.authentication.jwt import JWTManager
from shared.database.base import Base

fail_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
FailSession = async_sessionmaker(fail_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_failure_dbs():
    async with fail_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with fail_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_all_failure_modes_and_error_codes():
    jwt_mgr = JWTManager(secret_key="super_secret_jwt_key_for_development_purposes_min32chars")
    alice_token = jwt_mgr.create_access_token(
        user_id="alice_fail_id", email="alice@fail.com", role="USER"
    )

    async def get_test_user_service():
        async with FailSession() as session:
            yield user_main.UserService(user_main.UserRepository(session))

    async def get_test_product_service():
        async with FailSession() as session:
            yield product_main.ProductService(product_main.ProductRepository(session))

    async def get_test_order_service():
        async with FailSession() as session:
            yield order_main.OrderService(order_main.OrderRepository(session))

    async def get_test_payment_service():
        async with FailSession() as session:
            yield payment_main.PaymentService(
                payment_main.PaymentRepository(session),
                provider=payment_main.MockPaymentProvider(),
            )

    user_main.app.dependency_overrides[user_main.get_user_service] = get_test_user_service
    product_main.app.dependency_overrides[product_main.get_product_service] = (
        get_test_product_service
    )
    order_main.app.dependency_overrides[order_main.get_order_service] = get_test_order_service
    payment_main.app.dependency_overrides[payment_main.get_payment_service] = (
        get_test_payment_service
    )

    u_client = AsyncClient(transport=ASGITransport(app=user_main.app), base_url="http://test")
    p_client = AsyncClient(transport=ASGITransport(app=product_main.app), base_url="http://test")
    o_client = AsyncClient(transport=ASGITransport(app=order_main.app), base_url="http://test")
    pay_client = AsyncClient(transport=ASGITransport(app=payment_main.app), base_url="http://test")

    # 1. 401 Unauthorized - Missing Token
    res_401 = await u_client.get("/auth/me")
    assert res_401.status_code == 401
    assert res_401.json()["error"] == "UNAUTHORIZED"

    # 2. 401 Unauthorized - Invalid Login
    bad_login = await u_client.post(
        "/auth/login", json={"email": "nonexistent@user.com", "password": "wrong"}
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error"] == "INVALID_CREDENTIALS"

    # 3. 403 Forbidden - Regular User attempting admin action (create product)
    res_403 = await p_client.post(
        "/products",
        json={"name": "Hacker Item", "price": 10.0, "stock_quantity": 100},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_403.status_code == 403
    assert res_403.json()["error"] in ("FORBIDDEN", "INSUFFICIENT_PERMISSIONS")

    # 4. 404 Not Found - Non-existent product
    res_404 = await p_client.get("/products/non_existent_uuid")
    assert res_404.status_code == 404
    assert res_404.json()["error"] == "PRODUCT_NOT_FOUND"

    # 5. 422 Unprocessable Entity - Validation Error (Negative price)
    admin_token = jwt_mgr.create_access_token(
        user_id="admin_fail", email="admin@fail.com", role="ADMIN"
    )
    res_422 = await p_client.post(
        "/products",
        json={"name": "Bad Product", "price": -50.00, "stock_quantity": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_422.status_code == 422
    assert res_422.json()["error"] == "VALIDATION_ERROR"

    # 6. 400 Bad Request - Out of stock reservation
    prod_res = await p_client.post(
        "/products",
        json={"name": "Limited Item", "price": 100.0, "stock_quantity": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod_id = prod_res.json()["id"]

    over_reserve = await p_client.post(f"/products/{prod_id}/reserve", json={"quantity": 10})
    assert over_reserve.status_code == 400
    assert over_reserve.json()["error"] == "INSUFFICIENT_STOCK"

    # 7. 409 Conflict - Duplicate user registration
    await u_client.post(
        "/auth/register",
        json={
            "email": "first.reg@fail.com",
            "password": "Password123!",
            "first_name": "First",
            "last_name": "Reg",
        },
    )
    dup_res = await u_client.post(
        "/auth/register",
        json={
            "email": "first.reg@fail.com",
            "password": "Password123!",
            "first_name": "Second",
            "last_name": "Reg",
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"] == "USER_ALREADY_EXISTS"

    await u_client.aclose()
    await p_client.aclose()
    await o_client.aclose()
    await pay_client.aclose()
