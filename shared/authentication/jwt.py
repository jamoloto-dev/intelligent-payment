"""JWT token creation, OIDC validation, and decoding."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """Payload decoded from a valid JWT or OIDC access token."""

    sub: str  # user_id / subject identifier
    email: str
    role: str = "CUSTOMER"
    permissions: list[str] = Field(default_factory=list)
    auth_time: int | None = None
    amr: list[str] = Field(default_factory=list)
    iss: str | None = None
    aud: str | None = None
    exp: int
    iat: int
    jti: str | None = None


class JWTManager:
    """Manages JWT generation and verification with OIDC support."""

    def __init__(
        self,
        secret_key: str = "default_secret_for_dev_min_32_chars_long_entropy_key",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        issuer: str | None = None,
        audience: str | None = None,
        jwks_client: Any | None = None,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = jwks_client

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
            "auth_time": int(now.timestamp()),
            "amr": ["pwd"],
        }
        if self.issuer:
            payload["iss"] = self.issuer
        if self.audience:
            payload["aud"] = self.audience

        if custom_claims:
            payload.update(custom_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT/OIDC access token."""
        try:
            # 1. If JWKS client configured (e.g. Microsoft Entra / Auth0 / Clerk)
            if self.jwks_client:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                payload_dict = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256", self.algorithm],
                    issuer=self.issuer,
                    audience=self.audience,
                    options={"require": ["exp", "iat", "sub"]},
                )
            else:
                # 2. Symmetric key decoding
                options = {"require": ["exp", "iat", "sub"]}
                if not self.issuer:
                    options["verify_iss"] = False
                if not self.audience:
                    options["verify_aud"] = False

                payload_dict = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm, "HS256", "RS256"],
                    issuer=self.issuer,
                    audience=self.audience,
                    options=options,
                )

            # Map legacy roles/scopes if present
            if "role" not in payload_dict:
                roles = payload_dict.get("roles") or payload_dict.get(
                    "https://intelligentpay.io/roles"
                )
                if roles and isinstance(roles, list) and len(roles) > 0:
                    payload_dict["role"] = roles[0]
                else:
                    payload_dict["role"] = "CUSTOMER"

            return TokenPayload(**payload_dict)
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")
