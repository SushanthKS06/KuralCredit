from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import APP_VERSION
from app.api.router import api_router
from app.core.config import REPO_ROOT, get_settings
from app.core.constants import API_V1_PREFIX, REQUEST_ID_HEADER
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import configure_logging
from app.db.init_db import init_db
from app.observability.tracing import get_request_id, new_request_id, set_request_id

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level, redact=settings.log_redact_pii)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info(
        "application_startup",
        extra={"extra_fields": settings.redacted_diagnostics()},
    )
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title="KuralCredit",
    description=(
        "Voice-first multilingual loan-application clarification and evidence preparation. "
        "KuralCredit does not make credit decisions."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER, "Idempotency-Key"],
    expose_headers=[REQUEST_ID_HEADER, "Idempotent-Replay"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or new_request_id()
    set_request_id(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled_request_error",
            extra={"extra_fields": {"method": request.method, "path": request.url.path}},
        )
        raise
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith(API_V1_PREFIX):
        response.headers.setdefault("Cache-Control", "no-store")
    logger.info(
        "request_completed",
        extra={
            "extra_fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(elapsed_ms, 2),
            }
        },
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
            "request_id": get_request_id(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {key: value for key, value in error.items() if key not in {"input", "ctx"}}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "request_validation_error",
                "message": "The request could not be validated.",
                "details": details,
            },
            "request_id": get_request_id(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": (
                    "An unexpected error occurred. Please retry or contact the demo operator."
                ),
                "details": None,
            },
            "request_id": get_request_id(),
        },
    )


app.include_router(api_router, prefix=API_V1_PREFIX)

_FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
if (_FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def root():
    index = _FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        {
            "name": "KuralCredit",
            "version": APP_VERSION,
            "api": API_V1_PREFIX,
            "docs": "/docs",
            "message": "Frontend build not found. Run the frontend build for the full demo UI.",
        }
    )


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise NotFoundError("API endpoint not found")
    index = _FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    raise NotFoundError("Resource not found")
