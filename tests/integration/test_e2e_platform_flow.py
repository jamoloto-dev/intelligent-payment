"""End-to-End Platform Flow Integration Test."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import services.fraud_service.app.main as fraud_main
import services.order_service.app.main as order_main
import services.payment_service.app.main as payment_main
import services.product_service.app.main as product_main
import services.user_service.app.main as user_main
from shared.azure.tables import AuditTableStorage
from shared.database.base import Base
from shared.events.redis_client import EventBus

# DB setup for integration test with StaticPool
e2e_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
E2ESession = async_sessionmaker(e2e_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_integration_dbs():
    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_full_end_to_end_journey():
    bus = EventBus()
    audit_storage = AuditTableStorage(table_name="TestAudit")

    # Dependency overrides
    async def get_test_user_service():
        async with E2ESession() as session:
            yield user_main.UserService(user_main.UserRepository(session))

    async def get_test_product_service():
        async with E2ESession() as session:
            yield product_main.ProductService(product_main.ProductRepository(session))

    class DirectProductClient:
        def __init__(self, prod_app):
            self.app = prod_app

        async def reserve_stock(self, product_id: str, quantity: int):
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/products/{product_id}/reserve", json={"quantity": quantity})
                if resp.status_code != 200:
                    raise Exception(f"Product reservation failed: {resp.text}")
                data = resp.json()
                prod_resp = await ac.get(f"/products/{product_id}")
                data["product_name"] = prod_resp.json()["name"]
                return data

        async def release_stock(self, product_id: str, quantity: int):
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                await ac.post(f"/products/{product_id}/release", json={"quantity": quantity})

    product_client = DirectProductClient(product_main.app)

    async def get_test_order_service():
        async with E2ESession() as session:
            yield order_main.OrderService(
                order_main.OrderRepository(session),
                event_bus=bus,
                product_client=product_client,
            )

    class DirectFraudClient:
        def __init__(self, fraud_app):
            self.app = fraud_app

        async def check(
            self,
            transaction_id,
            order_id,
            user_id,
            amount,
            currency,
            billing_country=None,
            client_ip=None,
        ):
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    "/fraud/check",
                    json={
                        "transaction_id": transaction_id,
                        "order_id": order_id,
                        "user_id": user_id,
                        "amount": float(amount),
                        "currency": currency,
                        "billing_country": billing_country,
                        "client_ip": client_ip,
                    },
                )
                return resp.json()

    fraud_client = DirectFraudClient(fraud_main.app)

    async def get_test_payment_service():
        async with E2ESession() as session:
            yield payment_main.PaymentService(
                repository=payment_main.PaymentRepository(session),
                provider=payment_main.MockPaymentProvider(),
                event_bus=bus,
                fraud_client=fraud_client,
            )

    user_main.app.dependency_overrides[user_main.get_user_service] = get_test_user_service
    product_main.app.dependency_overrides[product_main.get_product_service] = (
        get_test_product_service
    )
    order_main.app.dependency_overrides[order_main.get_order_service] = get_test_order_service
    payment_main.app.dependency_overrides[payment_main.get_payment_service] = (
        get_test_payment_service
    )

    # Setup async clients
    user_client = AsyncClient(transport=ASGITransport(app=user_main.app), base_url="http://test")
    product_client_http = AsyncClient(
        transport=ASGITransport(app=product_main.app), base_url="http://test"
    )
    order_client = AsyncClient(transport=ASGITransport(app=order_main.app), base_url="http://test")
    payment_client = AsyncClient(
        transport=ASGITransport(app=payment_main.app), base_url="http://test"
    )
    fraud_client_http = AsyncClient(
        transport=ASGITransport(app=fraud_main.app), base_url="http://test"
    )

    # Step 1: Register User and Admin
    admin_reg = await user_client.post(
        "/auth/register",
        json={
            "email": "admin.e2e@platform.com",
            "password": "AdminPassword123!",
            "first_name": "Admin",
            "last_name": "System",
            "role": "ADMIN",
        },
    )
    assert admin_reg.status_code == 201

    user_reg = await user_client.post(
        "/auth/register",
        json={
            "email": "alice.e2e@customer.com",
            "password": "AlicePassword123!",
            "first_name": "Alice",
            "last_name": "Wonderland",
            "role": "USER",
        },
    )
    assert user_reg.status_code == 201
    alice_id = user_reg.json()["id"]

    # Step 2: Login
    admin_login = await user_client.post(
        "/auth/login",
        json={
            "email": "admin.e2e@platform.com",
            "password": "AdminPassword123!",
        },
    )
    admin_token = admin_login.json()["access_token"]

    alice_login = await user_client.post(
        "/auth/login",
        json={
            "email": "alice.e2e@customer.com",
            "password": "AlicePassword123!",
        },
    )
    alice_token = alice_login.json()["access_token"]

    # Step 3: Admin creates products in catalog
    p1_res = await product_client_http.post(
        "/products",
        json={
            "name": "Ergonomic Keyboard",
            "price": 120.00,
            "stock_quantity": 25,
            "currency": "USD",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert p1_res.status_code == 201
    p1_id = p1_res.json()["id"]

    p2_res = await product_client_http.post(
        "/products",
        json={
            "name": "UltraWide Monitor",
            "price": 450.00,
            "stock_quantity": 10,
            "currency": "USD",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert p2_res.status_code == 201
    p2_id = p2_res.json()["id"]

    # Step 4: Alice creates an order (2 keyboards + 1 monitor = $240 + $450 = $690)
    order_create_res = await order_client.post(
        "/orders",
        json={
            "items": [
                {"product_id": p1_id, "quantity": 2},
                {"product_id": p2_id, "quantity": 1},
            ],
            "shipping_address": "742 Evergreen Terrace, Springfield",
            "currency": "USD",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert order_create_res.status_code == 201
    order_data = order_create_res.json()
    assert order_data["status"] == "PENDING"
    assert float(order_data["total_amount"]) == 690.00
    assert len(order_data["items"]) == 2
    order_id = order_data["id"]

    # Verify inventory was decremented
    p1_check = await product_client_http.get(f"/products/{p1_id}")
    assert p1_check.json()["stock_quantity"] == 23

    p2_check = await product_client_http.get(f"/products/{p2_id}")
    assert p2_check.json()["stock_quantity"] == 9

    # Step 5: Alice processes payment for the order
    pay_res = await payment_client.post(
        "/payments",
        json={
            "order_id": order_id,
            "amount": 690.00,
            "currency": "USD",
            "payment_method_id": "pm_card_visa",
            "idempotency_key": f"idemp_{order_id}",
            "billing_country": "US",
        },
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert pay_res.status_code == 201
    pay_data = pay_res.json()
    assert pay_data["status"] == "SUCCEEDED"
    assert float(pay_data["amount"]) == 690.00
    payment_id = pay_data["id"]

    # Step 6: Verify Fraud Evaluation was recorded
    fraud_evals = await fraud_client_http.get(
        "/fraud/evaluations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert fraud_evals.status_code == 200
    assert len(fraud_evals.json()) >= 1

    # Step 7: Update order status to PAID
    status_update = await order_client.post(
        f"/orders/{order_id}/status",
        json={"status": "PAID"},
    )
    assert status_update.status_code == 200
    assert status_update.json()["status"] == "PAID"

    # Step 8: Alice retrieves her order and payment history
    final_order = await order_client.get(
        f"/orders/{order_id}", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert final_order.status_code == 200
    assert final_order.json()["status"] == "PAID"

    alice_payments = await payment_client.get(
        f"/payments/order/{order_id}", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert alice_payments.status_code == 200
    assert len(alice_payments.json()) == 1
    assert alice_payments.json()[0]["id"] == payment_id

    # Step 9: Audit record logging
    audit_record = await audit_storage.log_audit_event(
        partition_key="PaymentCompleted",
        event_type="PaymentCompleted",
        payload={"order_id": order_id, "payment_id": payment_id, "amount": 690.00},
    )
    assert audit_record["PartitionKey"] == "PaymentCompleted"

    # Cleanup clients
    await user_client.aclose()
    await product_client_http.aclose()
    await order_client.aclose()
    await payment_client.aclose()
    await fraud_client_http.aclose()
