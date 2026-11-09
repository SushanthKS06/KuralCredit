from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    applications,
    audit,
    capabilities,
    conversations,
    documents,
    facts,
    health,
    reconciliation,
    review,
    sessions,
    speech,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(capabilities.router)
api_router.include_router(workflows.router)
api_router.include_router(sessions.router)
api_router.include_router(applications.router)
api_router.include_router(speech.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(facts.router)
api_router.include_router(reconciliation.router)
api_router.include_router(audit.router)
api_router.include_router(review.router)
