"""User service API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from shared.authentication.dependencies import get_current_user_token, require_admin, require_authenticated
from shared.authentication.jwt import TokenPayload
from shared.schemas.common import PaginatedResponse, UserRole
from services.user_service.app.models.user import User
from services.user_service.app.repositories.user_repository import UserRepository
from services.user_service.app.schemas.user import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from services.user_service.app.services.user_service import UserService

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
users_router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(session: AsyncSession = Depends()) -> UserService:
    # Overridden in main.py with actual session dependency
    return UserService(UserRepository(session))


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, service: UserService = Depends(get_user_service)):
    """Register a new user account."""
    return await service.register(req)


@auth_router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, service: UserService = Depends(get_user_service)):
    """Authenticate and obtain JWT access token."""
    return await service.authenticate(req)


@auth_router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: TokenPayload = Depends(get_current_user_token),
    service: UserService = Depends(get_user_service),
):
    """Retrieve currently authenticated user profile."""
    return await service.get_by_id(current_user.sub)


@users_router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenPayload = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    """List users (Admin only)."""
    items, total = await service.list_users(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@users_router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: UserService = Depends(get_user_service),
):
    """Get user by ID (Self or Admin)."""
    if current_user.role != UserRole.ADMIN.value and current_user.sub != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to user profile"},
        )
    return await service.get_by_id(user_id)


@users_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    req: UserUpdateRequest,
    current_user: TokenPayload = Depends(require_authenticated),
    service: UserService = Depends(get_user_service),
):
    """Update user by ID (Self or Admin)."""
    if current_user.role != UserRole.ADMIN.value and current_user.sub != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to modify user profile"},
        )
    # Non-admin users cannot change role
    if current_user.role != UserRole.ADMIN.value and req.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Only admins can change roles"},
        )
    return await service.update(user_id, req)


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: TokenPayload = Depends(require_authenticated),
    service: UserService = Depends(get_user_service),
):
    """Delete user by ID (Self or Admin)."""
    if current_user.role != UserRole.ADMIN.value and current_user.sub != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Access denied to delete user profile"},
        )
    await service.delete(user_id)
