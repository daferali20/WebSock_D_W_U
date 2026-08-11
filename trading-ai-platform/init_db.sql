-- 1. تفعيل إضافة TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2. إنشاء جدول البيانات السعرية والسلاسل الزمنية
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

-- 3. تحويل الجدول إلى Hypertable مقسم زمنياً
SELECT create_hypertable('market_ticks', 'time', if_not_exists => TRUE);

-- 4. إنشاء الفهارس لتسريع استعلامات أحدث 200 نقطة لكل سهم
CREATE INDEX IF NOT EXISTS idx_symbol_time ON market_ticks (symbol, time DESC);

-- 5. ضغط البيانات القديمة (أقدم من 7 أيام) لتوفير المساحة وتسرع الاستعلامات
ALTER TABLE market_ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol'
);

SELECT add_compression_policy('market_ticks', INTERVAL '7 days', if_not_exists => TRUE);
