import os
import json
import logging
import signal
import sys
import databento as db
from confluent_kafka import Producer
from dotenv import load_dotenv

# إعداد السجلات (Logging)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

load_dotenv()

# قراءة الإعدادات من المتغيرات البيئية
DATABENTO_API_KEY = os.getenv("DATABENTO_API_KEY")
DATABENTO_DATASET = os.getenv("DATABENTO_DATASET", "XNAS.ITCH")
SYMBOLS = os.getenv("SYMBOLS", "AAPL").split(",")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "market-ticks")


def delivery_report(err, msg):
    """دالة التغذية الراجعة لتأكيد وصول الرسالة إلى Kafka"""
    if err is not None:
        logging.error(f"فشل إرسال الرسالة إلى Kafka: {err}")


def build_kafka_producer() -> Producer:
    """إنشاء ومكفالة الاتصال بـ Kafka Producer بأداء عالٍ"""
    kafka_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'client.id': 'databento-ingestion-producer',
        'compression.type': 'snappy',          # ضغط البيانات لتقليل استهلاك الشبكة
        'queue.buffering.max.messages': 200000,
        'linger.ms': 5,                        # تجميع الرسائل الخفيفة لزيادة الإنتاجية (Throughput)
    }
    return Producer(kafka_config)


def main():
    if not DATABENTO_API_KEY:
        logging.error("خطأ: لم يتم العثور على DATABENTO_API_KEY في المتغيرات البيئية.")
        sys.exit(1)

    producer = build_kafka_producer()
    logging.info(f"تم الاتصال بـ Kafka على: {KAFKA_BOOTSTRAP_SERVERS}")

    # إنشاء العميل اللحظي لـ Databento
    client = db.Live(key=DATABENTO_API_KEY)

    # الاشتراك في مخطط MBO (Market By Order) أو MBP-1 (Top of Book)
    client.subscribe(
        dataset=DATABENTO_DATASET,
        schema="mbp-1",  # إرسال أفضل سعر عرض/طلب + أحدث صفقات التداول
        symbols=SYMBOLS,
    )
    logging.info(f"بدء البث اللحظي لأسهم {SYMBOLS} من Databento ({DATABENTO_DATASET})...")

    def shutdown_handler(sig, frame):
        logging.info("جاري إيقاف الخدمة وتنظيف الاتصالات...")
        producer.flush(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        # الحلقة الرئيسية لاستقبال البيانات وبثها
        for record in client:
            # تحويل الأسعار من الصيغة الصحيحة المدمجة (Fixed-precision 1e9) إلى قيم عشرية
            price = getattr(record, "price", 0) / 1e9 if hasattr(record, "price") and record.price else None
            size = getattr(record, "size", 0)

            # تجهيز payload الأحداث
            payload = {
                "symbol": getattr(record, "symbol", "UNKNOWN"),
                "ts_event": record.ts_event,  # Timestamp بالنانوثانية
                "price": price,
                "size": size,
                "action": chr(getattr(record, "action", 78)), # N/A or Trade/Bid/Ask
                "side": chr(getattr(record, "side", 78)),
                "flags": getattr(record, "flags", 0)
            }

            # إرسال البيانات إلى Kafka بصيغة JSON مع مفتاح رمز السهم لتوزيع الـ Partitions
            producer.produce(
                topic=KAFKA_TOPIC,
                key=payload["symbol"].encode("utf-8"),
                value=json.dumps(payload).encode("utf-8"),
                callback=delivery_report
            )

            # معالجة أحداث Delivery Callbacks دون تعطيل الحلقة
            producer.poll(0)

    except Exception as e:
        logging.error(f"حدث خطأ غير متوقع أثناء استقبال البيانات: {e}")
    finally:
        logging.info("تفريغ الرسائل المتبقية في Kafka...")
        producer.flush()


if __name__ == "__main__":
    main()
