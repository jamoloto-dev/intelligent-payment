"""User database model."""

from sqlalchemy import Boolean, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base, TimestampMixin, UUIDMixin
from shared.schemas.common import UserRole


class User(Base, UUIDMixin, TimestampMixin):
    """User entity representing platform customers and administrators."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole, name="user_roles", values_callable=lambda x: [e.value for e in x]),
        default=UserRole.USER.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("ix_users_role_created", "role", "created_at"),)
