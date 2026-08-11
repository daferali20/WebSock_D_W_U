import os
import json
import logging
import sys
from datetime import datetime, timezone
import pandas as pd
import psycopg2
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from confluent_kafka import Producer
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

load_dotenv()

# الإعدادات المتغيرة
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "trading_db")
DB_USER = os.getenv("POSTGRES_USER", "trading_user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "trading_password")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "your_finnhub_key")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SIGNALS_TOPIC = os.getenv("SIGNALS_TOPIC", "ai-signals")
SYMBOLS = os.getenv("SYMBOLS", "AAPL,NVDA,MSFT").split(",")


def get_db_connection():
    """إنشاء اتصال بـ TimescaleDB"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )


def fetch_latest_ticks(symbol: str, limit: int = 200) -> pd.DataFrame:
    """سحب أحدث 200 نقطة بيانات لسهم معين وترتيبها زمنياً"""
    query = """
        SELECT time, symbol, price, volume, bid_depth, ask_depth
        FROM market_ticks
        WHERE symbol = %s
        ORDER BY time DESC
        LIMIT %s;
    """
    try:
        with get_db_connection() as conn:
            df = pd.read_sql(query, conn, params=(symbol, limit))
            if not df.empty:
                # أعِد الترتيب ليصبح تسلسلياً زمنياً (من القديم إلى الأحدث)
                df = df.iloc[::-1].reset_index(drop=True)
            return df
    except Exception as e:
        logging.error(f"خطأ أثناء سحب البيانات من TimescaleDB للسهم {symbol}: {e}")
        return pd.DataFrame()


def fetch_finnhub_sentiment(symbol: str) -> dict:
    """جلب بيانات المشاعر والأخبار من Finnhub API"""
    url = f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            sentiment_score = data.get("sentiment", {}).get("bullishPercent", 0.5)
            return {"sentiment_score": sentiment_score, "raw": data}
    except Exception as e:
        logging.warning(f"فشل جلب مشاعر Finnhub للسهم {symbol}: {e}")
    
    return {"sentiment_score": 0.50, "raw": {}}


def run_model_inference(symbol: str, ticks_df: pd.DataFrame, sentiment_data: dict) -> dict:
    """
    دالة محاكاة لاستنتاج النموذج (يمكن استبدالها بـ PyTorch / ONNX Runtime / Scikit-Learn)
    """
    current_price = float(ticks_df['price'].iloc[-1])
    sentiment_score = sentiment_data.get("sentiment_score", 0.5)
    
    # حساب متوسط متحرك بسيط كمثال توضيحي للميزات
    sma_20 = ticks_df['price'].tail(20).mean()
    bid_depth_sum = ticks_df['bid_depth'].sum()
    ask_depth_sum = ticks_df['ask_depth'].sum()

    # خوارزمية مبسطة أو استدعاء model.predict(X)
    confidence = round(min(0.50 + (sentiment_score * 0.3) + (0.1 if current_price > sma_20 else -0.1), 0.99), 2)
    action = "BUY" if confidence > 0.65 else ("SELL" if confidence < 0.35 else "HOLD")

    if action == "HOLD":
        return None  # لا يتم إرسال إشارة إذا كان القرار هو الانتظار

    target_price = round(current_price * (1.02 if action == "BUY" else 0.98), 2)
    stop_loss = round(current_price * (0.99 if action == "BUY" else 1.01), 2)

    return {
        "signal_id": f"sig_{symbol}_{int(datetime.now().timestamp())}",
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "current_price": current_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reasons": [
            f"مؤشر مشاعر Finnhub بنسبة {int(sentiment_score * 100)}%",
            f"عمق الطلبات الشرائية (Bid Depth): {int(bid_depth_sum)} مقابل العرض: {int(ask_depth_sum)}"
        ]
    }


def analyze_market_job(producer: Producer):
    """المهمة التي تعود كل 5 دقائق لتحليل جميع الأسهم"""
    logging.info("--- بدء دورة التحليل وتوليد الإشارات (كل 5 دقائق) ---")
    
    for symbol in SYMBOLS:
        # 1. سحب آخر 200 نقطة
        ticks_df = fetch_latest_ticks(symbol, limit=200)
        if ticks_df.empty or len(ticks_df) < 10:
            logging.warning(f"بيانات غير كافية للسهم {symbol} (المتوفر: {len(ticks_df)} نقاط)")
            continue

        # 2. جلب المشاعر
        sentiment = fetch_finnhub_sentiment(symbol)

        # 3. تشغيل النموذج
        signal = run_model_inference(symbol, ticks_df, sentiment)

        # 4. بث الإشارة إلى Kafka إذا توفرت
        if signal:
            producer.produce(
                topic=SIGNALS_TOPIC,
                key=symbol.encode("utf-8"),
                value=json.dumps(signal).encode("utf-8")
            )
            producer.flush()
            logging.info(f"تم إرسال إشارة جديدة [{signal['action']}] للسهم {symbol} بنسبة ثقة {signal['confidence']*100}%")

    logging.info("--- اكتملت دورة التحليل بنجاح ---")


def main():
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
    scheduler = BlockingScheduler()

    # تشغيل التحليل فوراً عند البدء، ثم تكراره كل 5 دقائق
    scheduler.add_job(
        func=analyze_market_job,
        args=[producer],
        trigger="interval",
        minutes=5,
        next_run_time=datetime.now()
    )

    logging.info("تم تشغيل محرك الذكاء الاصطناعي وجدولة المهام كل 5 دقائق...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("إيقاف محرك AI Engine...")


if __name__ == "__main__":
    main()
