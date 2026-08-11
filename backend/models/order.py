from sqlalchemy import String, Numeric, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import enum

from models.base import Base, UUIDMixin, TimestampMixin

class OrderSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Order(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orders"

    user_id: Mapped[UUIDMixin.id] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # مثل BTC-USDT
    side: Mapped[OrderSide] = mapped_column(SQLEnum(OrderSide), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(SQLEnum(OrderType), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, index=True)

    price: Mapped[Optional[float]] = mapped_column(Numeric(precision=18, scale=8), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    filled_quantity: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), default=0.0)

    # العلاقات
    user: Mapped["User"] = relationship("User", back_populates="orders")
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="order")

    __table_args__ = (
        Index("idx_orders_user_status", "user_id", "status"),
        Index("idx_orders_symbol_status", "symbol", "status"),
    )


class Trade(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "trades"

    order_id: Mapped[UUIDMixin.id] = mapped_column(ForeignKey("orders.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    execution_price: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    executed_quantity: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), default=0.0)

    # العلاقات
    order: Mapped["Order"] = relationship("Order", back_populates="trades")
