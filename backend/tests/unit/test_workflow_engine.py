from __future__ import annotations

import pytest

from app.core.exceptions import NotFoundError, ValidationAppError
from app.domain.workflow.registry import WorkflowRegistry
from app.domain.workflow.schema import (
    WorkflowDefinition,
    WorkflowFieldDefinition,
    WorkflowQuestionDefinition,
    WorkflowStageDefinition,
)


def test_registry_contains_reference_workflows():
    registry = WorkflowRegistry()
    workflows = registry.list_workflows()
    ids = {w.workflow_id for w in workflows}
    assert "loan_application" in ids
    assert "customer_support_intake" in ids

    loan_wf = registry.get("loan_application", version=1)
    assert loan_wf.workflow_id == "loan_application"
    assert loan_wf.workflow_version == 1
    assert "annual_sales" in loan_wf.field_by_id
    assert "bank_statement" in [d.id for d in loan_wf.document_profiles]

    support_wf = registry.get("customer_support_intake", version=1)
    assert support_wf.workflow_id == "customer_support_intake"
    assert support_wf.workflow_version == 1
    assert "customer_issue" in support_wf.field_by_id
    assert "urgency" in support_wf.field_by_id
    assert "annual_sales" not in support_wf.field_by_id


def test_registry_rejects_invalid_initial_stage():
    registry = WorkflowRegistry()
    invalid_wf = WorkflowDefinition(
        workflow_id="broken_workflow",
        workflow_version=1,
        display_name="Broken Workflow",
        description="Test",
        stages=[WorkflowStageDefinition(id="stage_one", label="Stage 1", order=1)],
        initial_stage="non_existent_stage",  # Invalid initial stage
        fields=[WorkflowFieldDefinition(id="f1", label="Field 1", type="string", required=True)],
        questions=[
            WorkflowQuestionDefinition(
                id="q1",
                field_key="f1",
                stage="stage_one",
                prompt="Prompt 1",
                reason="Reason",
                expected_answer_type="text",
            )
        ],
    )
    with pytest.raises(
        ValidationAppError, match="Initial stage 'non_existent_stage' is not in defined stages"
    ):
        registry.register(invalid_wf)


def test_registry_rejects_unbound_rule():
    registry = WorkflowRegistry()
    unbound_wf = WorkflowDefinition(
        workflow_id="unbound_rule_wf",
        workflow_version=1,
        display_name="Unbound Rule Workflow",
        description="Test",
        stages=[WorkflowStageDefinition(id="stage_one", label="Stage 1", order=1)],
        initial_stage="stage_one",
        fields=[WorkflowFieldDefinition(id="f1", label="Field 1", type="string", required=True)],
        questions=[
            WorkflowQuestionDefinition(
                id="q1",
                field_key="f1",
                stage="stage_one",
                prompt="Prompt 1",
                reason="Reason",
                expected_answer_type="text",
            )
        ],
        rules=["non_existent_magic_rule"],
    )
    with pytest.raises(
        ValidationAppError, match="unregistered rule plugin 'non_existent_magic_rule'"
    ):
        registry.register(unbound_wf)


def test_registry_rejects_invalid_field_type():
    registry = WorkflowRegistry()
    invalid_type_wf = WorkflowDefinition(
        workflow_id="invalid_type_wf",
        workflow_version=1,
        display_name="Invalid Type Workflow",
        description="Test",
        stages=[WorkflowStageDefinition(id="stage_one", label="Stage 1", order=1)],
        initial_stage="stage_one",
        fields=[
            # Pydantic schema will validate type, but if bypassed:
            WorkflowFieldDefinition.model_construct(
                id="f1", label="Field 1", type="unsupported_quantum_type", required=True
            )
        ],
        questions=[
            WorkflowQuestionDefinition(
                id="q1",
                field_key="f1",
                stage="stage_one",
                prompt="Prompt 1",
                reason="Reason",
                expected_answer_type="text",
            )
        ],
    )
    with pytest.raises(ValidationAppError, match="unknown type 'unsupported_quantum_type'"):
        registry.register(invalid_type_wf)


def test_registry_rejects_missing_workflow():
    registry = WorkflowRegistry()
    with pytest.raises(NotFoundError, match="Workflow 'does_not_exist' not found"):
        registry.get("does_not_exist")
