"""Order and OrderItem database models."""
from decimal import Decimal
from typing import List
from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.database.base import Base, TimestampMixin, UUIDMixin
from shared.schemas.common import OrderStatus


class Order(Base, UUIDMixin, TimestampMixin):
    """Customer order entity."""
    __tablename__ = "orders"

    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(OrderStatus, name="order_statuses", values_callable=lambda x: [e.value for e in x]),
        default=OrderStatus.PENDING.value,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Relationships
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="chk_positive_order_total"),
        Index("ix_orders_user_status", "user_id", "status"),
        Index("ix_orders_created", "created_at"),
    )


class OrderItem(Base, UUIDMixin, TimestampMixin):
    """Line item in a customer order."""
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_positive_quantity"),
        CheckConstraint("unit_price >= 0", name="chk_positive_unit_price"),
        CheckConstraint("subtotal >= 0", name="chk_positive_subtotal"),
    )
