import redis.asyncio as aioredis
from core.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

class OrderRedisManager:
    @staticmethod
    async def acquire_lock(user_id: str, lock_key: str, ttl_seconds: int = 2) -> bool:
        """
        منع الصفقات المكررة بنفس الثانية من نفس المستخدم (Idempotency)
        """
        key = f"lock:order:{user_id}:{lock_key}"
        # setnx تعيد True إذا كان المفتاح غير موجود
        is_set = await redis_client.set(key, "locked", nx=True, ex=ttl_seconds)
        return bool(is_set)

    @staticmethod
    async def cache_active_order(order_id: str, order_data: dict, ttl: int = 3600):
        key = f"active_order:{order_id}"
        await redis_client.hset(key, mapping=order_data)
        await redis_client.expire(key, ttl)

    @staticmethod
    async def get_cached_order(order_id: str) -> dict:
        key = f"active_order:{order_id}"
        return await redis_client.hgetall(key)
