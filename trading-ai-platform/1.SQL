-- جدول السلاسل الزمنية لبيانات السوق
CREATE TABLE market_ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price NUMERIC(12, 4),
    volume INT,
    bid_depth NUMERIC(12, 2),
    ask_depth NUMERIC(12, 2)
);

-- تحويل الجدول إلى Hypertable خاص بـ TimescaleDB لتسريع استعلامات أحدث 200 نقطة
SELECT create_hypertable('market_ticks', 'time');
CREATE INDEX idx_symbol_time ON market_ticks (symbol, time DESC);
