# syntax=docker/dockerfile:1.7
# Multi-stage build -> a single image that serves both the API and the SPA.
# Build context is the repo root:  docker build -f deploy/docker/Dockerfile -t bi-portal .

# --------------------------------------------------------------------------- #
# Stage 1: build the React SPA
# --------------------------------------------------------------------------- #
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# vite.config.ts defaults outDir to ../backend/static (for native dev builds);
# inside the image we emit to a local ./dist and copy it into the runtime stage.
RUN npx vite build --outDir dist --emptyOutDir

# --------------------------------------------------------------------------- #
# Stage 2: python runtime
# --------------------------------------------------------------------------- #
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps kept minimal; psycopg2-binary & snowflake wheels are self-contained.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
# Built SPA served as static files by FastAPI (see app/main.py).
COPY --from=frontend /fe/dist ./static

# Run as a non-root user.
RUN useradd -m -u 10001 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
