"""Unit tests for API Gateway."""
import pytest
from httpx import ASGITransport, AsyncClient
from services.api_gateway.app.main import app


@pytest.mark.asyncio
async def test_gateway_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "api-gateway"
        assert data["status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_gateway_ready():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "api-gateway"
        assert "user-service" in data["dependencies"]


@pytest.mark.asyncio
async def test_gateway_unknown_route_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/nonexistent/resource")
        assert res.status_code == 404
        assert res.json()["error"] == "ROUTE_NOT_FOUND"


@pytest.mark.asyncio
async def test_gateway_downstream_unavailable():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Route to /auth/me when user-service is not running on localhost:8001
        res = await ac.get("/auth/me")
        assert res.status_code == 503
        assert res.json()["error"] == "SERVICE_UNAVAILABLE"
