from __future__ import annotations

import logging

from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.workflow.definitions.customer_support_intake import (
    CUSTOMER_SUPPORT_INTAKE_WORKFLOW,
)
from app.domain.workflow.definitions.loan_application import (
    LOAN_APPLICATION_WORKFLOW,
)
from app.domain.workflow.plugins.registry import get_rule_registry
from app.domain.workflow.schema import WorkflowDefinition, WorkflowSummary

logger = logging.getLogger(__name__)

ALLOWED_FIELD_TYPES = {"string", "text", "money", "number", "enum", "boolean", "date"}
ALLOWED_TRANSITION_CONDITIONS = {
    "all_fields_present",
    "document_uploaded",
    "clarifications_resolved",
    "custom_rule",
}


class WorkflowRegistry:
    """Central versioned registry for voice workflows.

    Validates workflow schemas at registration to prevent invalid transitions,
    unsupported field types, or unbound rules from entering production.
    """

    def __init__(self) -> None:
        self._workflows: dict[tuple[str, int], WorkflowDefinition] = {}
        # Pre-register the standard reference workflows
        self.register(LOAN_APPLICATION_WORKFLOW)
        self.register(CUSTOMER_SUPPORT_INTAKE_WORKFLOW)

    def validate(self, workflow: WorkflowDefinition) -> list[str]:
        errors: list[str] = []
        if not workflow.workflow_id or not workflow.workflow_id.strip():
            errors.append("Workflow ID cannot be empty.")
        if workflow.workflow_version < 1:
            errors.append("Workflow version must be >= 1.")

        stage_ids = {s.id for s in workflow.stages}
        if workflow.initial_stage not in stage_ids:
            errors.append(
                f"Initial stage '{workflow.initial_stage}' is not in defined stages: {stage_ids}."
            )

        field_ids = set()
        for f in workflow.fields:
            if f.id in field_ids:
                errors.append(f"Duplicate field ID: '{f.id}'.")
            field_ids.add(f.id)
            if f.type not in ALLOWED_FIELD_TYPES:
                errors.append(
                    f"Field '{f.id}' has unknown type '{f.type}'. Allowed: {ALLOWED_FIELD_TYPES}."
                )
            if f.type == "enum" and not f.allowed_values:
                errors.append(f"Enum field '{f.id}' must declare allowed_values.")

        question_ids = set()
        for q in workflow.questions:
            if q.id in question_ids:
                errors.append(f"Duplicate question ID: '{q.id}'.")
            question_ids.add(q.id)
            if q.stage not in stage_ids:
                errors.append(f"Question '{q.id}' references unknown stage '{q.stage}'.")

        for t in workflow.transitions:
            if t.from_stage not in stage_ids:
                errors.append(f"Transition references unknown from_stage '{t.from_stage}'.")
            if t.to_stage not in stage_ids:
                errors.append(f"Transition references unknown to_stage '{t.to_stage}'.")
            if t.condition not in ALLOWED_TRANSITION_CONDITIONS:
                errors.append(f"Transition has unsupported condition '{t.condition}'.")

        rule_registry = get_rule_registry()
        for rule_name in workflow.rules:
            if not rule_registry.get(rule_name):
                errors.append(f"Workflow references unregistered rule plugin '{rule_name}'.")

        return errors

    def register(self, workflow: WorkflowDefinition) -> None:
        errors = self.validate(workflow)
        if errors:
            raise ValidationAppError(
                f"Workflow validation failed for {workflow.workflow_id}: {'; '.join(errors)}"
            )
        key = (workflow.workflow_id, workflow.workflow_version)
        self._workflows[key] = workflow
        logger.info(
            "workflow_registered",
            extra={
                "extra_fields": {"id": workflow.workflow_id, "version": workflow.workflow_version}
            },
        )

    def get(self, workflow_id: str, version: int | str | None = None) -> WorkflowDefinition:
        if version is not None:
            parsed_version: int
            if isinstance(version, int):
                parsed_version = version
            elif isinstance(version, str):
                cleaned = version.strip().lstrip("vV").split(".")[0]
                try:
                    parsed_version = int(cleaned)
                except ValueError:
                    parsed_version = -1
            else:
                try:
                    parsed_version = int(version)
                except (TypeError, ValueError):
                    parsed_version = -1
            key = (workflow_id, parsed_version)
            wf = self._workflows.get(key)
            if wf is None:
                raise NotFoundError(f"Workflow '{workflow_id}' version {version} not found")
            return wf

        # Find highest version for this workflow_id
        candidates = [wf for (w_id, _), wf in self._workflows.items() if w_id == workflow_id]
        if not candidates:
            raise NotFoundError(f"Workflow '{workflow_id}' not found")
        return max(candidates, key=lambda w: w.workflow_version)

    def list_workflows(self) -> list[WorkflowSummary]:
        # Return latest version of each unique workflow
        by_id: dict[str, WorkflowDefinition] = {}
        for (w_id, _), wf in self._workflows.items():
            if w_id not in by_id or wf.workflow_version > by_id[w_id].workflow_version:
                by_id[w_id] = wf

        summaries: list[WorkflowSummary] = []
        for wf in by_id.values():
            summaries.append(
                WorkflowSummary(
                    workflow_id=wf.workflow_id,
                    workflow_version=wf.workflow_version,
                    display_name=wf.display_name,
                    description=wf.description,
                    category=wf.category,
                    supported_languages=wf.supported_languages,
                    input_modes=wf.input_modes,
                    required_field_count=len(wf.required_fields),
                    has_documents=len(wf.document_profiles) > 0,
                    human_review_required=wf.human_review_required,
                )
            )
        return sorted(summaries, key=lambda s: s.workflow_id)


_default_registry = WorkflowRegistry()


def get_workflow_registry() -> WorkflowRegistry:
    return _default_registry
