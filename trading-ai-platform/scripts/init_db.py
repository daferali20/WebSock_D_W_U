import os
import time
import logging
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
load_dotenv()

# إعدادات الاتصال من المتغيرات البيئية أو استخدام الإعدادات الافتراضية للـ Docker
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "trading_db")
DB_USER = os.getenv("POSTGRES_USER", "trading_user")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "trading_password")

INIT_SQL = """
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price NUMERIC(12, 4),
    volume INT,
    bid_depth NUMERIC(12, 2),
    ask_depth NUMERIC(12, 2),
    action CHAR(1),
    side CHAR(1)
);

SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_symbol_time ON market_ticks (symbol, time DESC);

ALTER TABLE market_ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('market_ticks', INTERVAL '7 days', if_not_exists => TRUE);
"""

def initialize_timescaledb(max_retries: int = 10, delay: int = 3):
    """الاتصال بـ TimescaleDB وتنفيذ أسباب التهيئة مع محاولات إعادتها عند عدم الجاهزية"""
    connection = None
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"محاولة الاتصال بـ TimescaleDB ({attempt}/{max_retries})...")
            connection = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS
            )
            connection.autocommit = True
            
            with connection.cursor() as cursor:
                logging.info("جاري تهيئة الإضافات والجداول والـ Hypertable...")
                cursor.execute(INIT_SQL)
                
            logging.info("تمت تهيئة قاعدة البيانات TimescaleDB بنجاح!")
            break

        except psycopg2.OperationalError as e:
            logging.warning(f"قاعدة البيانات غير جاهزة بعد: {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                logging.error("فشل الاتصال بقاعدة البيانات بعد استنفاد جميع المحاولات.")
                raise e
        finally:
            if connection:
                connection.close()

if __name__ == "__main__":
    initialize_timescaledb()
