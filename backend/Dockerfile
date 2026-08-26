FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libzbar0 poppler-utils \
        tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/app /app/backend/app
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app/backend

COPY backend /app/backend
COPY src /app/src
COPY data /app/data
COPY templates /app/templates

RUN mkdir -p /app/storage/uploads /app/storage/reports \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app/storage

USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
