from enum import StrEnum

from shared.authentication.jwt import TokenPayload


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    USER = "USER"  # Backward-compatible alias for CUSTOMER
    SUPPORT = "SUPPORT"
    OPERATIONS = "OPERATIONS"
    FINANCE = "FINANCE"
    FRAUD_ANALYST = "FRAUD_ANALYST"
    ADMIN = "ADMIN"
    OWNER = "OWNER"


# Standard Least-Privilege Role Permission Matrix
ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.CUSTOMER: {
        "profile:read_own",
        "profile:write_own",
        "orders:create",
        "orders:read_own",
        "payments:create",
        "payments:read_own",
    },
    Role.USER: {
        "profile:read_own",
        "profile:write_own",
        "orders:create",
        "orders:read_own",
        "payments:create",
        "payments:read_own",
    },
    Role.SUPPORT: {
        "profile:read_own",
        "orders:read_all",
        "orders:read_own",
        "payments:read_all",
        "payments:read_own",
        "users:read",
    },
    Role.OPERATIONS: {
        "profile:read_own",
        "products:create",
        "products:update",
        "products:stock",
        "health:read_all",
        "orders:read_all",
        "orders:read_own",
    },
    Role.FINANCE: {
        "profile:read_own",
        "payments:refund",
        "payments:read_all",
        "payments:read_own",
        "orders:read_all",
        "orders:read_own",
    },
    Role.FRAUD_ANALYST: {
        "profile:read_own",
        "fraud:review",
        "fraud:read_all",
        "fraud:override",
        "payments:read_all",
        "payments:read_own",
        "orders:read_all",
        "orders:read_own",
    },
    Role.ADMIN: {
        "profile:read_own",
        "profile:write_own",
        "orders:create",
        "orders:read_own",
        "orders:read_all",
        "payments:create",
        "payments:read_own",
        "payments:read_all",
        "payments:refund",
        "products:create",
        "products:update",
        "products:stock",
        "fraud:review",
        "fraud:read_all",
        "fraud:override",
        "users:read",
        "users:read_all",
        "users:write",
        "users:manage_roles",
        "audit:read",
        "health:read_all",
    },
    Role.OWNER: {
        "*",  # Superuser wildcard
        "system:config",
        "system:secrets",
    },
}


def get_user_permissions(user: TokenPayload) -> set[str]:
    """Derive full effective permissions for a user from their role and token claims."""
    # 1. Base permissions from assigned role
    role_norm = user.role.upper()
    perms = set(ROLE_PERMISSIONS.get(role_norm, set()))

    # 2. Add explicit token claims (e.g., fine-grained OIDC scopes/permissions)
    if hasattr(user, "permissions") and user.permissions:
        perms.update(user.permissions)

    return perms


__all__ = [
    "Role",
    "ROLE_PERMISSIONS",
    "get_user_permissions",
]
