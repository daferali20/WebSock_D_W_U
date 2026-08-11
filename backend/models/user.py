from sqlalchemy import String, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from models.base import Base, UUIDMixin, TimestampMixin

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(String(20), default="user")

    # العلاقات
    wallets: Mapped[List["Wallet"]] = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")


class Wallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallets"

    user_id: Mapped[UUIDMixin.id] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)  # مثل BTC, USDT
    balance: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), default=0.0, nullable=False)
    locked_balance: Mapped[float] = mapped_column(Numeric(precision=18, scale=8), default=0.0, nullable=False)  # الرصيد المحجوز للأوامر المعلقة

    # العلاقات
    user: Mapped["User"] = relationship("User", back_populates="wallets")

    __table_args__ = (
        Index("idx_user_currency", "user_id", "currency", unique=True),
    )
