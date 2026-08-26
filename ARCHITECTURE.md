# Architecture

## Overview

Репозиторий содержит два интерфейса над одной Python business logic:

- legacy Streamlit для резервного запуска;
- Modern Web: Next.js frontend и FastAPI backend.

```mermaid
flowchart LR
    Browser[Browser] --> Next[Next.js frontend]
    Next --> API[FastAPI REST API]
    API --> Auth[Authentication]
    API --> Services[Application services]
    Services --> Core[Existing src core]
    Core --> OCR[PDF / QR / OCR]
    Core --> DOCX[DOCX generation]
    Services --> DB[(SQLite dev / PostgreSQL prod)]
    Services --> Storage[(Upload and output storage)]
    Legacy[Legacy Streamlit app.py] --> Core
    Legacy --> LegacyData[(employees.json / output)]
```

## Repository layout

```text
app.py, streamlit_app.py     legacy Streamlit entrypoints
src/                         shared Pydantic models, parsers and generators
backend/app/                 FastAPI routes, schemas, services and persistence
backend/tests/               API and service tests
backend/alembic/             database migrations
frontend/src/app/            Next.js routes
frontend/src/components/     application and UI components
frontend/src/features/       report, employee and history flows
frontend/src/**/*.test.*     Vitest component/unit tests
frontend/e2e/                Playwright browser tests
templates/                   existing DOCX templates
data/                        legacy employee directory and autofill profiles
storage/                     web uploads and generated files, gitignored
```

## Backend boundaries

- API routes parse HTTP input and apply authorization.
- Pydantic schemas define every public request and response.
- Services own report orchestration, uploads, history and employee operations.
- Services own focused SQLAlchemy persistence; routes do not query models directly.
- `src/` owns receipt recognition, validation, document context and DOCX generation.
- FastAPI and shared core do not import Streamlit.

## Persistence

SQLite is the local default. The same SQLAlchemy models support PostgreSQL in production through `DATABASE_URL`.

Persistent entities:

- users, roles and one-to-one employee account links;
- employees;
- uploaded receipt metadata;
- reports and validated input snapshots;
- generated file metadata.

Binary files remain in configurable filesystem storage. Database rows never contain whole DOCX/PDF binaries.

## Authorization

- `admin` sees the dashboard, all reports, employee directory and account settings.
- `employee` can upload receipts, generate a report only for its linked `employee_id`, open the newly generated result and download its files.
- Both roles use the employee-directory email as the login; the initial admin is linked to `drugalev`.
- Dashboard, report list and account management are protected by backend role dependencies; frontend route guards only mirror these server-side rules.

## Generation pipeline

```mermaid
sequenceDiagram
    participant UI as Next.js
    participant API as FastAPI
    participant Core as src core
    participant DB as Database
    participant FS as File storage

    UI->>API: upload receipt
    API->>FS: validate and save
    API->>Core: parse receipt
    Core-->>API: structured Receipt
    API-->>UI: editable receipt data
    UI->>API: generate typed report
    API->>DB: create processing record
    API->>Core: validate and build DOCX
    Core->>FS: write generated files
    API->>DB: store result metadata
    API-->>UI: report and download links
```

## Security model

- email/password login with Argon2 hashes;
- signed JWT in an HttpOnly cookie;
- `admin` and `employee` roles enforced by backend dependencies;
- upload extension, MIME, file-signature, filename and size validation;
- per-report storage directories;
- configured CORS allowlist;
- no runtime package installation in backend request handlers;
- no absolute developer-machine paths in application source.

## Deployment

Docker Compose provides PostgreSQL, backend and production Next.js for a VPS. The root `Dockerfile` packages Next.js, FastAPI and OCR into one cloud container; a persistent `/app/storage` volume holds SQLite, uploads and generated files. Next.js proxies same-origin `/api` requests to FastAPI.
