import json
from aiokafka import AIOKafkaProducer
from core.config import settings
import logging

logger = logging.getLogger("order_service_kafka")

class OrderKafkaProducer:
    def __init__(self):
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await self.producer.start()
        logger.info("تم الاتصال بـ Kafka Producer بنجاح.")

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_order_event(self, event_type: str, order_data: dict):
        if not self.producer:
            raise RuntimeError("Kafka Producer غير متصل")
            
        payload = {
            "event": event_type,
            "data": order_data
        }
        await self.producer.send_and_wait("orders_topic", payload)
        logger.info(f"تم إرسال الحدث [{event_type}] إلى كافكا بنجاح.")

kafka_producer = OrderKafkaProducer()
