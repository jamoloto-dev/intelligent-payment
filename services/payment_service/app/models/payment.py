"""Payment database model."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.database.base import Base, TimestampMixin, UUIDMixin
from shared.schemas.common import PaymentStatus


class Payment(Base, UUIDMixin, TimestampMixin):
    """Payment transaction record."""

    __tablename__ = "payments"

    order_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="stripe", nullable=False)
    provider_transaction_id: Mapped[str] = mapped_column(String(100), index=True, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            PaymentStatus, name="payment_statuses", values_callable=lambda x: [e.value for e in x]
        ),
        default=PaymentStatus.PENDING.value,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), index=True, nullable=True)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_positive_payment_amount"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_idempotency"),
        Index("ix_payments_order_status", "order_id", "status"),
        Index("ix_payments_created", "created_at"),
    )
