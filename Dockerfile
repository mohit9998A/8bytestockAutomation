# Lightweight image for Dagster user code
FROM python:3.11-slim

WORKDIR /opt/dagster/app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy project files first for cache efficiency
COPY pyproject.toml .
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

# Copy the rest of the code
COPY . .

ENV DAGSTER_HOME=/opt/dagster/dagster_home
RUN mkdir -p $DAGSTER_HOME

# Default command is unused because dagster-webserver/daemon run in separate containers
CMD ["python", "-m", "stock_pipeline"]
