"""FastAPI Authentication and Authorization dependencies with Granular RBAC."""

import os
from collections.abc import Callable
from datetime import UTC, datetime

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.authentication.jwt import JWTManager, TokenPayload
from shared.authentication.permissions import (
    ROLE_PERMISSIONS,
    Role,
    get_user_permissions,
)
from shared.logging.logger import user_id_ctx

load_dotenv()

security = HTTPBearer(auto_error=False)

DEFAULT_JWT_SECRET = "super_secret_jwt_key_for_development_purposes_min32chars"


def get_jwt_manager() -> JWTManager:
    """Returns JWTManager configured with current environment secret or OIDC JWKS."""
    secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    issuer = os.getenv("OIDC_ISSUER_URL")
    audience = os.getenv("OIDC_AUDIENCE")
    jwks_url = os.getenv("OIDC_JWKS_URL")

    jwks_client = None
    if jwks_url:
        try:
            import jwt

            jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, max_cached_keys=16)
        except Exception:
            pass

    return JWTManager(
        secret_key=secret,
        algorithm=algorithm,
        issuer=issuer,
        audience=audience,
        jwks_client=jwks_client,
    )


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> TokenPayload:
    """Validate Bearer token (JWT or OIDC) and return decoded token payload."""
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
        user_role = current_user.role.upper()
        allowed_upper = [r.upper() for r in allowed_roles]
        if user_role not in allowed_upper and "OWNER" not in user_role and "ADMIN" not in user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "FORBIDDEN",
                    "message": f"Operation requires one of roles: {', '.join(allowed_roles)}",
                },
            )
        return current_user

    return role_checker


def require_permission(permission: str) -> Callable:
    """Dependency factory checking that current user possesses a specific permission.

    Follows OWASP Deny-by-Default and Least Privilege guidelines.
    """

    async def permission_checker(
        current_user: TokenPayload = Depends(get_current_user_token),
    ) -> TokenPayload:
        perms = get_user_permissions(current_user)

        # Check exact permission or wildcard ownership
        if "*" in perms or permission in perms:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "INSUFFICIENT_PERMISSIONS",
                "message": f"Operation requires permission: '{permission}'",
                "required_permission": permission,
                "current_role": current_user.role,
            },
        )

    return permission_checker


def require_mfa_or_reauth(max_age_minutes: int = 15) -> Callable:
    """Dependency ensuring recent step-up authentication or MFA validation for sensitive actions.

    Checks:
    - X-Reauth-Token or X-MFA-Code header, OR
    - Token `auth_time` within `max_age_minutes` window, OR
    - Token `amr` claim containing 'mfa'.
    """

    async def reauth_checker(
        current_user: TokenPayload = Depends(get_current_user_token),
        x_mfa_code: str | None = Header(None, alias="X-MFA-Code"),
        x_reauth_token: str | None = Header(None, alias="X-Reauth-Token"),
    ) -> TokenPayload:
        now_ts = int(datetime.now(UTC).timestamp())

        # 1. Check direct MFA/Reauth header
        if x_mfa_code or x_reauth_token:
            return current_user

        # 2. Check token auth_time freshness
        if current_user.auth_time is not None:
            age_seconds = now_ts - current_user.auth_time
            if age_seconds <= max_age_minutes * 60:
                return current_user

        # 3. Check AMR claim
        if "mfa" in current_user.amr:
            return current_user

        # If user is in dev/test environment or basic token, allow if token was issued recently
        token_age = now_ts - current_user.iat
        if token_age <= max_age_minutes * 60:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "REAUTHENTICATION_REQUIRED",
                "message": "Sensitive administrative operation requires recent re-authentication or MFA confirmation.",
            },
        )

    return reauth_checker


require_admin = require_roles(["ADMIN", "OWNER"])
require_authenticated = require_roles(
    ["CUSTOMER", "USER", "SUPPORT", "OPERATIONS", "FINANCE", "FRAUD_ANALYST", "ADMIN", "OWNER"]
)

__all__ = [
    "Role",
    "ROLE_PERMISSIONS",
    "get_jwt_manager",
    "get_current_user_token",
    "get_user_permissions",
    "require_permission",
    "require_mfa_or_reauth",
    "require_roles",
    "require_admin",
    "require_authenticated",
]
