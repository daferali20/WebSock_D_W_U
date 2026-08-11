import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, status, Depends

from services.order_service.schemas import (
    OrderCreateSchema, OrderResponseSchema, OrderStatus, OrderType
)
from services.order_service.kafka_producer import kafka_producer
from services.order_service.redis_cache import OrderRedisManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # بدء تشغيل الاتصال مع Kafka عند بدء التطبيق
    await kafka_producer.start()
    yield
    # إغلاق اتصالات Kafka عند إيقاف التطبيق
    await kafka_producer.stop()

app = FastAPI(title="Order Service", lifespan=lifespan)

@app.post("/orders", response_model=OrderResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreateSchema,
    x_user_id: str = Header(..., alias="X-User-ID")  # يتم تمريره عبر الـ API Gateway
):
    # 1. التحقق من منطق الطلب (LIMIT يتطلب سِعراً)
    if order_in.order_type == OrderType.LIMIT and not order_in.price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يجب تحديد السعر لأوامر الحد (LIMIT Orders)."
        )

    # 2. الحماية من التكرار عبر Redis Lock
    lock_key = f"{order_in.symbol}:{order_in.side}:{order_in.quantity}"
    acquired = await OrderRedisManager.acquire_lock(x_user_id, lock_key)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تم استلام طلب مماثل معالج حالياً. يرجى الانتظار."
        )

    # 3. إنشاء معرف الأمر وتجهيز الكائن
    order_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    order_data = {
        "order_id": order_id,
        "user_id": x_user_id,
        "symbol": order_in.symbol,
        "side": order_in.side.value,
        "order_type": order_in.order_type.value,
        "price": str(order_in.price) if order_in.price else "0.0",
        "quantity": str(order_in.quantity),
        "status": OrderStatus.PENDING.value,
        "created_at": now.isoformat()
    }

    # 4. تخزين الأمر مؤقتاً في Redis للوصول السريع
    await OrderRedisManager.cache_active_order(order_id, order_data)

    # 5. إرسال حدث إنشاء الأمر إلى Kafka لمعالجته عبر Matching Engine أو البورصة
    await kafka_producer.send_order_event("ORDER_CREATED", order_data)

    return OrderResponseSchema(
        order_id=order_id,
        user_id=x_user_id,
        symbol=order_in.symbol,
        side=order_in.side,
        order_type=order_in.order_type,
        price=order_in.price,
        quantity=order_in.quantity,
        status=OrderStatus.PENDING,
        created_at=now
    )

@app.get("/orders/{order_id}")
async def get_order_status(
    order_id: str,
    x_user_id: str = Header(..., alias="X-User-ID")
):
    # محاولة الاستعلام من Redis أولاً لسرعة الأداء
    cached_order = await OrderRedisManager.get_cached_order(order_id)
    if cached_order:
        if cached_order.get("user_id") != x_user_id:
            raise HTTPException(status_code=403, detail="غير مصرح للاطلاع على هذا الأمر.")
        return cached_order

    # في حال عدم وجوده بـ Redis يتم الاستعلام من قاعدة البيانات الرئيسية (SQLAlchemy)
    raise HTTPException(status_code=404, detail="الأمر غير موجود.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
