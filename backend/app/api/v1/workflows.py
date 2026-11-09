from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.domain.workflow.registry import get_workflow_registry
from app.domain.workflow.schema import WorkflowDefinition, WorkflowSummary

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowSummary])
def list_workflows() -> list[WorkflowSummary]:
    """List all available workflows in the system."""
    return get_workflow_registry().list_workflows()


@router.get("/{workflow_id}", response_model=WorkflowDefinition)
def get_workflow(workflow_id: str, version: int | None = None) -> WorkflowDefinition:
    """Retrieve full configuration and schema for a specific workflow."""
    try:
        return get_workflow_registry().get(workflow_id, version=version)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/validate")
def validate_workflow(workflow: WorkflowDefinition) -> dict[str, Any]:
    """Validate a candidate workflow definition without registering it."""
    errors = get_workflow_registry().validate(workflow)
    return {
        "valid": len(errors) == 0,
        "workflow_id": workflow.workflow_id,
        "workflow_version": workflow.workflow_version,
        "errors": errors,
    }
