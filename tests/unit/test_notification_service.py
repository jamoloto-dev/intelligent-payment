"""Unit and API tests for Notification Service."""
import pytest
from httpx import ASGITransport, AsyncClient
from shared.authentication.jwt import JWTManager
from shared.events.redis_client import EventBus
from services.notification_service.app.config.settings import settings
from services.notification_service.app.consumers.event_consumer import NotificationEventConsumer
from services.notification_service.app.main import app
from services.notification_service.app.routers.notification_router import get_notification_service
from services.notification_service.app.schemas.notification import NotificationSendRequest, NotificationType
from services.notification_service.app.services.notification_service import NotificationService
from services.notification_service.app.storage.storage import NotificationStorage

test_storage = NotificationStorage()
test_service = NotificationService(storage=test_storage)


async def override_get_notification_service():
    yield test_service


app.dependency_overrides[get_notification_service] = override_get_notification_service

jwt_mgr = JWTManager(secret_key=settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
admin_token = jwt_mgr.create_access_token(user_id="admin_notif", email="admin@notif.com", role="ADMIN")
user_token = jwt_mgr.create_access_token(user_id="user_notif", email="customer@example.com", role="USER")


@pytest.mark.asyncio
async def test_manual_notification_dispatch():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/notifications/send",
            json={
                "recipient": "customer@example.com",
                "subject": "Welcome to Intelligent Payment",
                "body": "Your account is activated.",
                "notification_type": "LOG",
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 201
        data = res.json()
        assert data["recipient"] == "customer@example.com"
        assert data["status"] == "SENT"

        # Query user notifications
        list_res = await ac.get("/notifications", headers={"Authorization": f"Bearer {user_token}"})
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 1
        assert items[0]["recipient"] == "customer@example.com"


@pytest.mark.asyncio
async def test_event_consumer_order_and_payment():
    bus = EventBus()
    consumer = NotificationEventConsumer(event_bus=bus, notification_service=test_service)

    # Order Created
    await consumer.handle_order_created({
        "order_id": "ord_event_1",
        "user_id": "usr_event_1",
        "user_email": "event_buyer@example.com",
        "total_amount": "199.99",
        "currency": "USD",
    })

    # Payment Completed
    await consumer.handle_payment_completed({
        "payment_id": "pay_event_1",
        "order_id": "ord_event_1",
        "user_id": "usr_event_1",
        "user_email": "event_buyer@example.com",
        "amount": "199.99",
        "currency": "USD",
    })

    records = await test_storage.list_notifications(recipient="event_buyer@example.com")
    assert len(records) == 2
    assert records[0].event_type == "OrderCreated"
    assert records[1].event_type == "PaymentCompleted"
