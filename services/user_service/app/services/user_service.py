"""User service business logic layer."""

from fastapi import HTTPException, status

from services.user_service.app.config.settings import settings
from services.user_service.app.models.user import User
from services.user_service.app.repositories.user_repository import UserRepository
from services.user_service.app.schemas.user import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from shared.authentication.jwt import JWTManager
from shared.authentication.password import hash_password, verify_password
from shared.logging.logger import get_logger
from shared.schemas.common import UserRole

logger = get_logger("user-service")


class UserService:
    """Handles user registration, authentication, and management."""

    def __init__(self, repository: UserRepository):
        self.repository = repository
        self.jwt_manager = JWTManager(
            secret_key=settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
            access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    async def register(self, req: UserRegisterRequest) -> UserResponse:
        existing = await self.repository.get_by_email(req.email)
        if existing:
            logger.warning(f"Registration failed: email {req.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "USER_ALREADY_EXISTS",
                    "message": "A user with this email already exists",
                },
            )

        hashed = hash_password(req.password)
        user = User(
            email=req.email.lower(),
            password_hash=hashed,
            first_name=req.first_name,
            last_name=req.last_name,
            role=req.role.value if req.role else UserRole.USER.value,
        )
        created_user = await self.repository.create(user)
        logger.info(f"Registered new user: {created_user.id} ({created_user.email})")
        return UserResponse.model_validate(created_user)

    async def authenticate(self, req: UserLoginRequest) -> TokenResponse:
        user = await self.repository.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            logger.warning(f"Authentication failed for email: {req.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "INVALID_CREDENTIALS", "message": "Invalid email or password"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "ACCOUNT_DISABLED", "message": "User account has been disabled"},
            )

        token = self.jwt_manager.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def get_by_id(self, user_id: str) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "USER_NOT_FOUND", "message": f"User {user_id} not found"},
            )
        return UserResponse.model_validate(user)

    async def update(self, user_id: str, req: UserUpdateRequest) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "USER_NOT_FOUND", "message": f"User {user_id} not found"},
            )

        if req.email and req.email.lower() != user.email:
            existing = await self.repository.get_by_email(req.email)
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": "EMAIL_IN_USE", "message": "Email is already taken"},
                )
            user.email = req.email.lower()

        if req.first_name is not None:
            user.first_name = req.first_name
        if req.last_name is not None:
            user.last_name = req.last_name
        if req.role is not None:
            user.role = req.role.value
        if req.is_active is not None:
            user.is_active = req.is_active

        updated_user = await self.repository.update(user)
        return UserResponse.model_validate(updated_user)

    async def delete(self, user_id: str) -> None:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "USER_NOT_FOUND", "message": f"User {user_id} not found"},
            )
        await self.repository.delete(user)

    async def list_users(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[UserResponse], int]:
        users, total = await self.repository.list_users(page, page_size)
        return [UserResponse.model_validate(u) for u in users], total
