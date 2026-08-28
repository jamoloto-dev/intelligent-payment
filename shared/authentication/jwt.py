"""JWT token creation and decoding."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Payload decoded from a valid JWT."""

    sub: str  # user_id
    email: str
    role: str
    exp: int
    iat: int
    jti: str | None = None


class JWTManager:
    """Manages JWT generation and verification."""

    def __init__(
        self,
        secret_key: str = "default_secret_for_dev_min_32_chars_long_entropy_key",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes

    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str,
        expires_delta: timedelta | None = None,
        custom_claims: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(UTC)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }
        if custom_claims:
            payload.update(custom_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT access token."""
        try:
            payload_dict = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"require": ["exp", "iat", "sub"]},
            )
            return TokenPayload(**payload_dict)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
