from contextlib import contextmanager
from sqlalchemy import create_engine, text
import os

def build_pg_url() -> str:
    user = os.getenv("POSTGRES_USER", "stockuser")
    pwd = os.getenv("POSTGRES_PASSWORD", "stockpass")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB", "stocks")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"

@contextmanager
def get_conn():
    engine = create_engine(build_pg_url(), pool_pre_ping=True)
    with engine.begin() as conn:
        yield conn

def upsert_rows(conn, rows):
    if not rows:
        return 0
    stmt = text("""        INSERT INTO stock_prices (symbol, trading_day, open, high, low, close, adjusted_close, volume)
        VALUES (:symbol, :trading_day, :open, :high, :low, :close, :adjusted_close, :volume)
        ON CONFLICT (symbol, trading_day) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            adjusted_close = EXCLUDED.adjusted_close,
            volume = EXCLUDED.volume
    """)
    conn.execute(stmt, rows)
    return len(rows)
