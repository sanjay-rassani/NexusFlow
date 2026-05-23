# ──────────────────────────────────────────────
# Stage 1: Builder — install Python dependencies
# ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System deps for psycopg2 and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements/production.txt .
RUN pip install --prefix=/install -r production.txt


# ──────────────────────────────────────────────
# Stage 2: Runtime — lean production image
# ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# Runtime-only system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/ .

# Create non-root user for security
RUN groupadd -r nexusflow && useradd -r -g nexusflow nexusflow \
    && mkdir -p /var/log/nexusflow /app/staticfiles /app/media \
    && chown -R nexusflow:nexusflow /app /var/log/nexusflow

USER nexusflow

EXPOSE 8000

# Daphne serves both HTTP and WebSocket
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
