import os, time, json, traceback
from datetime import datetime
from typing import Dict, List
import requests
from dagster import job, op, get_dagster_logger, ScheduleDefinition, Definitions, Failure
from .utils.db import get_conn, upsert_rows

def fetch_alpha_vantage(symbol: str) -> Dict:
    base_url = os.getenv("ALPHAVANTAGE_BASE_URL", "https://www.alphavantage.co/query")
    api_key = os.getenv("ALPHAVANTAGE_API_KEY")
    function = os.getenv("ALPHAVANTAGE_FUNCTION", "TIME_SERIES_DAILY_ADJUSTED")
    if not api_key:
        raise ValueError("ALPHAVANTAGE_API_KEY is not set")

    params = {
        "function": function,
        "symbol": symbol,
        "apikey": api_key,
        "outputsize": "compact"  # up to ~100 points
    }
    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # API sends errors in JSON too
    if "Error Message" in data or "Note" in data:
        raise RuntimeError(f"API error for {symbol}: {data.get('Error Message') or data.get('Note')}")
    return data

def parse_alpha_vantage(symbol: str, payload: Dict) -> List[Dict]:
    # Detect the time series key regardless of chosen function
    ts_key = next((k for k in payload.keys() if "Time Series" in k), None)
    if not ts_key:
        return []
    series = payload.get(ts_key, {})
    rows = []
    for day, vals in series.items():
        try:
            rows.append({
                "symbol": symbol.upper(),
                "trading_day": datetime.strptime(day, "%Y-%m-%d").date(),
                "open": float(vals.get("1. open")) if vals.get("1. open") else None,
                "high": float(vals.get("2. high")) if vals.get("2. high") else None,
                "low": float(vals.get("3. low")) if vals.get("3. low") else None,
                "close": float(vals.get("4. close")) if vals.get("4. close") else None,
                "adjusted_close": float(vals.get("5. adjusted close") or vals.get("4. close")) if (vals.get("5. adjusted close") or vals.get("4. close")) else None,
                "volume": int(vals.get("6. volume") or vals.get("5. volume") or 0),
            })
        except Exception:
            # skip malformed row
            continue
    return rows

@op
def fetch_symbols() -> list[str]:
    symbols = os.getenv("STOCK_SYMBOLS", "AAPL,MSFT").split(",")
    symbols = [s.strip() for s in symbols if s.strip()]
    if not symbols:
        raise Failure("No symbols configured via STOCK_SYMBOLS")
    return symbols

@op
def fetch_data_for_symbol(symbol: str) -> dict:
    log = get_dagster_logger()
    retries = 3
    backoff = 5
    for attempt in range(1, retries+1):
        try:
            data = fetch_alpha_vantage(symbol)
            return {"symbol": symbol, "payload": data}
        except Exception as e:
            log.warning(f"[{symbol}] fetch attempt {attempt} failed: {e}")
            if attempt == retries:
                # Return a marker so downstream can skip
                return {"symbol": symbol, "payload": None, "error": str(e)}
            time.sleep(backoff * attempt)

@op
def extract_rows(fetch_result: dict) -> list[dict]:
    symbol = fetch_result.get("symbol")
    payload = fetch_result.get("payload")
    if not payload:
        # return empty list; handled gracefully
        return []
    return parse_alpha_vantage(symbol, payload)

@op
def upsert_to_postgres(rows: list[dict]) -> int:
    if not rows:
        return 0
    with get_conn() as conn:
        count = upsert_rows(conn, rows)
    return count

@job
def stock_ingest_job():
    symbols = fetch_symbols()
    # Simple fan-in pattern
    upserted_counts = []
    for s in symbols:
        fr = fetch_data_for_symbol(s)
        rows = extract_rows(fr)
        c = upsert_to_postgres(rows)
        upserted_counts.append(c)
    # Dagster tracks outputs; no need to return explicitly

# Schedule (configurable via env var)
cron = os.getenv("SCHEDULE_CRON", "@daily")
stock_schedule = ScheduleDefinition(job=stock_ingest_job, cron_schedule=cron)

defs = Definitions(jobs=[stock_ingest_job], schedules=[stock_schedule])
