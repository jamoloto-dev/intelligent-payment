"""Unit tests for API Gateway readiness, routing, error handling, and rate limiting."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient, Response

from services.api_gateway.app.main import app
from services.api_gateway.app.middleware.rate_limit import RateLimitMiddleware


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
async def test_gateway_ready_returns_503_when_downstream_unavailable():
    """Readiness probe must return HTTP 503 when downstream dependencies are unreachable."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["service"] == "api-gateway"
        assert data["status"] == "DEGRADED"
        assert "user-service" in data["dependencies"]


@pytest.mark.asyncio
async def test_gateway_ready_returns_200_when_all_healthy():
    """Readiness probe returns HTTP 200 when all microservices respond with 200 OK."""
    transport = ASGITransport(app=app)
    mock_resp = Response(200, json={"status": "HEALTHY"})

    with patch("services.api_gateway.app.main.http_client.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/ready")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "HEALTHY"


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
        res = await ac.get("/auth/me")
        assert res.status_code == 503
        assert res.json()["error"] == "SERVICE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_gateway_rate_limiting_enforcement():
    """Verify rate limiter blocks bursts exceeding the configured threshold with 429."""
    limiter = RateLimitMiddleware(app=app, max_requests_per_minute=3)

    # Simulated client requests
    client_ip = "192.168.1.100"
    now = 1000.0

    # 1st, 2nd, 3rd request: allowed
    exceeded1, rem1, _ = limiter._check_rate_limit_memory(client_ip, now)
    assert not exceeded1
    assert rem1 == 2

    exceeded2, rem2, _ = limiter._check_rate_limit_memory(client_ip, now + 1)
    assert not exceeded2
    assert rem2 == 1

    exceeded3, rem3, _ = limiter._check_rate_limit_memory(client_ip, now + 2)
    assert not exceeded3
    assert rem3 == 0

    # 4th request: rejected with 429 rate limit exceeded
    exceeded4, rem4, _ = limiter._check_rate_limit_memory(client_ip, now + 3)
    assert exceeded4
    assert rem4 == 0
