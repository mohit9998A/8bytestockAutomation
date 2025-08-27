# Dockerized Data Pipeline with Dagster (Stocks -> PostgreSQL)

This project provides a production-style, Docker Compose–based data pipeline using **Dagster** to fetch stock market prices from **Alpha Vantage** and upsert them into **PostgreSQL**. It includes robust error handling, environment-based secrets, and a daily schedule (cron configurable).

## Features
- **Fetch**: Pulls JSON data from Alpha Vantage (`TIME_SERIES_DAILY_ADJUSTED` by default).
- **Process & Store**: Parses OHLCV and upserts into `stock_prices` (PostgreSQL) with a primary key `(symbol, trading_day)`.
- **Orchestrate**: Dagster job with a schedule (`@daily` by default).
- **Robustness**: Retries, JSON error checks, missing-data tolerance, idempotent upsert.
- **Security**: API key and DB credentials via environment variables.
- **Dockerized**: One-command bring-up with `docker compose up -d`.

## Quick Start

1. **Download/clone** this folder, then create `.env` from the sample:
   ```bash
   cp .env.sample .env
   ```

2. **Edit `.env`**:
   - Set `ALPHAVANTAGE_API_KEY` (free key: https://www.alphavantage.co/support/#api-key).
   - Optionally change `STOCK_SYMBOLS` (comma separated).
   - For hourly runs, set `SCHEDULE_CRON="0 * * * *"`.

3. **Start everything** (from the project root):
   ```bash
   docker compose up -d --build
   ```

4. **Open Dagster UI** at http://localhost:3000 — find and run `stock_ingest_job` (or let the schedule trigger it).

5. **Check data**:
   ```bash
   docker exec -it stock_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT * FROM stock_prices ORDER BY trading_day DESC LIMIT 10;"
   ```

## Project Layout
```
.
├── .env.sample            # Copy to .env and fill secrets
├── docker-compose.yml     # Orchestrates Postgres + Dagster (webserver, daemon, code)
├── initdb/
│   └── 01_create_table.sql
└── dagster_project/
    ├── Dockerfile
    ├── pyproject.toml
    ├── dagster.yaml
    ├── workspace.yaml
    └── src/stock_pipeline/
        ├── __init__.py
        ├── repository.py     # Exposes Dagster Definitions
        ├── jobs.py           # Job, ops, schedule, API & DB logic
        └── utils/db.py       # Postgres URL + upsert helpers
```

## How it Works

- **API**: Calls Alpha Vantage using `requests` with `function=TIME_SERIES_DAILY_ADJUSTED` (configurable).
- **Parsing**: Extracts OHLCV fields and gracefully skips malformed rows.
- **Database**: Performs `INSERT ... ON CONFLICT DO UPDATE` on `(symbol, trading_day)` to make the job idempotent.
- **Scheduling**: Controlled by `SCHEDULE_CRON` (e.g., `@daily`, `0 * * * *` for hourly).
- **Resilience**: 3 fetch attempts with exponential backoff; JSON error/Note handling (rate-limit protection).

## Customize

- **Symbols**: Set `STOCK_SYMBOLS` in `.env` (e.g., `AAPL,MSFT,GOOGL,RELIANCE.BSE,TCS.BSE`).
- **Function**: Change `ALPHAVANTAGE_FUNCTION` (e.g., `TIME_SERIES_INTRADAY` with interval param—extend code accordingly).
- **Table**: Edit `initdb/01_create_table.sql` and `utils/db.py` mapping as needed.

## Security Notes

- Secrets should live only in `.env` (never commit your real `.env` to Git).
- Rotate `ALPHAVANTAGE_API_KEY` if leaked.

## Troubleshooting

- **Rate limits**: Free Alpha Vantage is rate-limited. Use fewer symbols or add sleep; or upgrade plan.
- **Networking**: If webserver can't see code, ensure `DAGSTER_DEFAULT_LOCATION_NAME` matches and volumes are mounted.
- **DB auth**: Verify `.env` DB values match `docker-compose.yml`.

## License
MIT
