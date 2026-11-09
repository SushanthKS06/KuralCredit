from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import APP_VERSION
from app.api.deps import get_db_dep, get_registry_dep, get_settings_dep
from app.core.config import Settings
from app.providers.registry import ProviderRegistry
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    providers = registry.health()
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=APP_VERSION,
        environment=settings.app_env,
        database=database,
        providers=providers,
    )


@router.get("/health/ready", response_model=HealthResponse)
def readiness(
    db: Session = Depends(get_db_dep),
    settings: Settings = Depends(get_settings_dep),
    registry: ProviderRegistry = Depends(get_registry_dep),
) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    providers = registry.health()
    ready = database == "ok" and settings.gnani_configured and settings.groq_configured
    return HealthResponse(
        status="ready" if ready else "degraded",
        version=APP_VERSION,
        environment=settings.app_env,
        database=database,
        providers=providers,
    )
