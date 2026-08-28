"""Unit and API tests for User Service."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from services.user_service.app.main import app
from services.user_service.app.repositories.user_repository import UserRepository
from services.user_service.app.routers.user_router import get_user_service
from services.user_service.app.services.user_service import UserService
from shared.database.base import Base

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_user_service():
        async with TestingSessionLocal() as session:
            yield UserService(UserRepository(session))

    app.dependency_overrides[get_user_service] = override_get_user_service
    yield
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_user_registration_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/auth/register",
            json={
                "email": "jane.doe@example.com",
                "password": "SecurePassword123!",
                "first_name": "Jane",
                "last_name": "Doe",
                "role": "USER",
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "jane.doe@example.com"
    assert data["first_name"] == "Jane"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_user_duplicate_email_conflict():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "Password123!",
                "first_name": "First",
                "last_name": "User",
            },
        )
        response = await ac.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "Password123!",
                "first_name": "Second",
                "last_name": "User",
            },
        )
    assert response.status_code == 409
    assert response.json()["error"] == "USER_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_user_login_success_and_failure():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "login.test@example.com",
                "password": "CorrectPassword123!",
                "first_name": "Login",
                "last_name": "Tester",
            },
        )

        # Correct login
        login_res = await ac.post(
            "/auth/login",
            json={"email": "login.test@example.com", "password": "CorrectPassword123!"},
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # Incorrect password
        bad_login = await ac.post(
            "/auth/login", json={"email": "login.test@example.com", "password": "WrongPassword!"}
        )
        assert bad_login.status_code == 401
        assert bad_login.json()["error"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_auth_me_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post(
            "/auth/register",
            json={
                "email": "me.test@example.com",
                "password": "Password123!",
                "first_name": "Me",
                "last_name": "Tester",
            },
        )
        login_res = await ac.post(
            "/auth/login", json={"email": "me.test@example.com", "password": "Password123!"}
        )
        token = login_res.json()["access_token"]

        me_res = await ac.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "me.test@example.com"
