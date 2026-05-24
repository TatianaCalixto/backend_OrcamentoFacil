# OrçaFácil — Dockerfile de produção do backend (Sprint 16-T01)
# Multi-stage para minimizar tamanho final.

# ============================================================
# Stage 1: build (instala dependências em wheels)
# ============================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# system deps necessárias para compilar bcrypt/psycopg quando wheels faltarem
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ============================================================
# Stage 2: runtime (imagem enxuta com user não-root)
# ============================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH"

# usuário não-root
RUN useradd --create-home --shell /bin/bash app

# libpq runtime (psycopg precisa em runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# copia deps instaladas do builder
COPY --from=builder /root/.local /home/app/.local
RUN chown -R app:app /home/app/.local

WORKDIR /app

COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# uvicorn com workers; em prod usar 2-4 workers por core
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
