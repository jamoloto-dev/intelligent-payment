"""Tests for strict authorization boundaries across all service routes."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import services.payment_service.app.main as payment_main
import services.product_service.app.main as product_main
import services.user_service.app.main as user_main
from services.payment_service.app.models.payment import Payment
from services.payment_service.app.providers.mock_provider import MockPaymentProvider
from shared.authentication.jwt import JWTManager
from shared.database.base import Base
from shared.schemas.common import PaymentStatus

auth_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
AuthSession = async_sessionmaker(auth_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_auth_db():
    async with auth_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with auth_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


jwt_mgr = JWTManager(secret_key="super_secret_jwt_key_for_development_purposes_min32chars")
alice_token = jwt_mgr.create_access_token(
    user_id="alice_user_id", email="alice@test.com", role="USER"
)
bob_token = jwt_mgr.create_access_token(user_id="bob_user_id", email="bob@test.com", role="USER")
admin_token = jwt_mgr.create_access_token(
    user_id="admin_user_id", email="admin@test.com", role="ADMIN"
)


@pytest.mark.asyncio
async def test_user_service_authorization_boundaries():
    """Verify User service boundaries for self vs admin vs unauthorized."""

    async def get_test_user_service():
        async with AuthSession() as session:
            yield user_main.UserService(user_main.UserRepository(session))

    user_main.app.dependency_overrides[user_main.get_user_service] = get_test_user_service

    async with AsyncClient(
        transport=ASGITransport(app=user_main.app), base_url="http://test"
    ) as ac:
        # Register Alice
        reg = await ac.post(
            "/auth/register",
            json={
                "email": "alice_boundary@test.com",
                "password": "Password123!",
                "first_name": "A",
                "last_name": "B",
            },
        )
        alice_id = reg.json()["id"]
        token_res = await ac.post(
            "/auth/login", json={"email": "alice_boundary@test.com", "password": "Password123!"}
        )
        a_token = token_res.json()["access_token"]

        # 1. Unauthenticated /auth/me -> 401
        res_401 = await ac.get("/auth/me")
        assert res_401.status_code == 401

        # 2. Non-admin accessing /users list -> 403
        res_403 = await ac.get("/users", headers={"Authorization": f"Bearer {a_token}"})
        assert res_403.status_code == 403

        # 3. Non-admin attempting to access another user profile -> 403
        other_user_res = await ac.get(
            "/users/other_user_id", headers={"Authorization": f"Bearer {a_token}"}
        )
        assert other_user_res.status_code == 403

        # 4. Admin accessing /users list -> 200
        admin_res = await ac.get("/users", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_res.status_code == 200


@pytest.mark.asyncio
async def test_product_service_admin_boundaries():
    """Verify only Admins can create/modify products; users can only read."""

    async def get_test_product_service():
        async with AuthSession() as session:
            yield product_main.ProductService(product_main.ProductRepository(session))

    product_main.app.dependency_overrides[product_main.get_product_service] = (
        get_test_product_service
    )

    async with AsyncClient(
        transport=ASGITransport(app=product_main.app), base_url="http://test"
    ) as ac:
        # 1. Regular user creating product -> 403
        user_create = await ac.post(
            "/products",
            json={"name": "Sneaky Product", "price": 50.0, "stock_quantity": 5},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert user_create.status_code == 403

        # 2. Admin creating product -> 201
        admin_create = await ac.post(
            "/products",
            json={"name": "Authorized Product", "price": 50.0, "stock_quantity": 5},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_create.status_code == 201
        prod_id = admin_create.json()["id"]

        # 3. Public/User reading product -> 200
        read_res = await ac.get(f"/products/{prod_id}")
        assert read_res.status_code == 200


@pytest.mark.asyncio
async def test_payment_service_tenant_boundaries():
    """Verify Bob cannot view or refund Alice's payment record."""

    async def get_test_payment_service():
        async with AuthSession() as session:
            repo = payment_main.PaymentRepository(session)
            yield payment_main.PaymentService(
                repository=repo,
                provider=MockPaymentProvider(),
            )

    payment_main.app.dependency_overrides[payment_main.get_payment_service] = (
        get_test_payment_service
    )

    # Seed a payment owned by Alice
    async with AuthSession() as session:
        alice_payment = Payment(
            id="pay_alice_123",
            order_id="ord_alice_1",
            user_id="alice_user_id",
            amount=Decimal("100.00"),
            currency="USD",
            provider="mock",
            status=PaymentStatus.SUCCEEDED.value,
        )
        session.add(alice_payment)
        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(app=payment_main.app), base_url="http://test"
    ) as ac:
        # 1. Bob accessing Alice's payment -> 403 Forbidden
        bob_get = await ac.get(
            "/payments/pay_alice_123", headers={"Authorization": f"Bearer {bob_token}"}
        )
        assert bob_get.status_code == 403

        # 2. Bob attempting to refund Alice's payment -> 403 Forbidden
        bob_refund = await ac.post(
            "/payments/pay_alice_123/refund",
            json={"amount": 100.00},
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert bob_refund.status_code == 403

        # 3. Alice accessing her own payment -> 200 OK
        alice_get = await ac.get(
            "/payments/pay_alice_123", headers={"Authorization": f"Bearer {alice_token}"}
        )
        assert alice_get.status_code == 200

        # 4. Admin accessing Alice's payment -> 200 OK
        admin_get = await ac.get(
            "/payments/pay_alice_123", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_get.status_code == 200
