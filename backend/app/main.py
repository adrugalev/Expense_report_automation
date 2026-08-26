from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import accounts, auth, dashboard, employees, health, meta, reports, uploads
from .config import get_settings
from .database import SessionLocal, create_database_schema
from .seed import seed_initial_data


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.prepare_directories()
    create_database_schema()
    with SessionLocal() as session:
        seed_initial_data(session, settings)
    logger.info("Expense Report API started in %s mode", settings.environment)
    yield
    logger.info("Expense Report API stopped")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

if settings.host_allowlist:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.host_allowlist)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Проверьте заполнение формы",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Не удалось выполнить операцию"}},
    )


for router in (health.router, meta.router, auth.router, accounts.router, dashboard.router, employees.router, uploads.router, reports.router):
    app.include_router(router, prefix="/api")
