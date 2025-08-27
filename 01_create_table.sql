-- Creates a table to store daily stock OHLCV
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol TEXT NOT NULL,
    trading_day DATE NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    adjusted_close NUMERIC,
    volume BIGINT,
    PRIMARY KEY (symbol, trading_day)
);
