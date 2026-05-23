# Celery worker image — identical runtime to backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt

COPY backend/ .

RUN groupadd -r nexusflow && useradd -r -g nexusflow nexusflow
USER nexusflow

# Default: start both worker and beat (split these in production)
CMD ["celery", "-A", "config", "worker", "--loglevel=info", "--concurrency=4"]
