"""FastAPI Authentication and Authorization dependencies."""

import os
from collections.abc import Callable

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.authentication.jwt import JWTManager, TokenPayload
from shared.logging.logger import user_id_ctx

security = HTTPBearer(auto_error=False)

DEFAULT_JWT_SECRET = "super_secret_jwt_key_for_development_purposes_min32chars"


def get_jwt_manager() -> JWTManager:
    """Returns JWTManager configured with current environment secret."""
    secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    return JWTManager(secret_key=secret, algorithm=algorithm)


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> TokenPayload:
    """Validate Bearer token and return the payload."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Missing or invalid authentication token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        jwt_mgr = get_jwt_manager()
        payload = jwt_mgr.decode_token(credentials.credentials)
        user_id_ctx.set(payload.sub)
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_TOKEN", "message": str(e)},
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(allowed_roles: list[str]) -> Callable:
    """Dependency factory checking that current user has one of allowed roles."""

    async def role_checker(
        current_user: TokenPayload = Depends(get_current_user_token),
    ) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "FORBIDDEN",
                    "message": f"Operation requires one of roles: {', '.join(allowed_roles)}",
                },
            )
        return current_user

    return role_checker


require_admin = require_roles(["ADMIN"])
require_authenticated = require_roles(["USER", "ADMIN"])
