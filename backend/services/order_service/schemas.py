from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderCreateSchema(BaseModel):
    symbol: str = Field(..., example="BTC-USDT")
    side: OrderSide
    order_type: OrderType
    price: Optional[float] = Field(None, description="مطلوب فقط في حالة طلب الحد LIMIT")
    quantity: float = Field(..., gt=0, description="الكمية يجب أن تكون أكبر من 0")

class OrderResponseSchema(OrderCreateSchema):
    order_id: str
    user_id: str
    status: OrderStatus
    created_at: datetime

    class Config:
        from_attributes = True
