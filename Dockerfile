FROM node:22-bookworm-slim AS frontend-dependencies

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable

WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile


FROM frontend-dependencies AS frontend-builder

ARG BACKEND_INTERNAL_URL=http://127.0.0.1:8000
ENV BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL

COPY frontend ./
RUN pnpm build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    STORAGE_DIR=/app/storage \
    DATABASE_URL=sqlite:////app/storage/expense_web.db \
    TEMPLATES_DIR=/app/templates \
    LEGACY_DATA_DIR=/app/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libzbar0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node

WORKDIR /app
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app/backend

COPY backend /app/backend
COPY src /app/src
COPY data /app/data
COPY templates /app/templates
COPY vendor /app/vendor
COPY --from=frontend-builder /build/frontend/.next/standalone /app/frontend
COPY --from=frontend-builder /build/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /build/frontend/public /app/frontend/public

RUN mkdir -p /app/storage/uploads /app/storage/reports \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app/storage

USER appuser
EXPOSE 3000

CMD ["python", "-m", "backend.app.cloud_entrypoint"]
