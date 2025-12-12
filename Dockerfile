# Multi-purpose Dockerfile for DailyMood Flask app
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends curl \ 
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure SQLite directory exists
RUN mkdir -p /app/data

ENV FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000 \
    DATABASE_URL=sqlite:////app/data/dailymood.db \
    SECRET_KEY=change-me

EXPOSE 5000

# Container-level healthcheck hits lightweight endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=5s \
    CMD curl -f http://127.0.0.1:5000/health || exit 1

# Create entrypoint script for initialization
RUN echo '#!/bin/sh' > /app/entrypoint.sh && \
    echo 'set -e' >> /app/entrypoint.sh && \
    echo 'echo "Checking database..."' >> /app/entrypoint.sh && \
    echo '# db.create_all() тільки створює таблиці, якщо їх немає - не видаляє існуючі дані' >> /app/entrypoint.sh && \
    echo 'python -c "from app import db, app; app.app_context().push(); db.create_all(); print(\"Database ready\")"' >> /app/entrypoint.sh && \
    echo 'echo "Starting gunicorn..."' >> /app/entrypoint.sh && \
    echo 'exec gunicorn -b 0.0.0.0:5000 app:app' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
