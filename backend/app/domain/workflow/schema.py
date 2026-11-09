from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowFieldDefinition(BaseModel):
    id: str = Field(..., description="Unique field identifier across the workflow")
    label: str = Field(..., description="Human-readable label for applicant and reviewer UI")
    type: Literal["string", "text", "money", "number", "enum", "boolean", "date"] = Field(
        ..., description="Data type of the field"
    )
    required: bool = Field(
        default=True, description="Whether this field is required for submission"
    )
    description: str = Field(default="", description="Detailed explanation or guidance")
    measure_type: str = Field(
        default="general", description="Measure category for reconciliation/rules"
    )
    source_type: str = Field(default="applicant_text", description="Default source type")
    allowed_values: list[str] | None = Field(
        default=None, description="Allowed choices if type is enum"
    )
    default_period: str | None = Field(
        default=None, description="Default temporal period if applicable"
    )
    validation_rules: list[str] = Field(
        default_factory=list, description="Field-level validator rule names"
    )


class WorkflowQuestionDefinition(BaseModel):
    id: str = Field(..., description="Unique question identifier")
    field_key: str = Field(..., description="Target field key populated by this question")
    stage: str = Field(..., description="Workflow stage during which this question is presented")
    prompt: str = Field(..., description="Default question prompt text")
    reason: str = Field(..., description="Reviewer-facing reason why this question is asked")
    expected_answer_type: Literal["text", "amount", "number", "document", "choice"] = Field(
        ..., description="Expected answer format"
    )
    priority: int = Field(default=100, description="Ordering priority (lower numbers asked first)")
    branch_conditions: dict[str, Any] | None = Field(
        default=None, description="Optional conditional branching criteria"
    )


class WorkflowDocumentProfile(BaseModel):
    id: str = Field(..., description="Document profile type identifier (e.g. bank_statement)")
    label: str = Field(..., description="Human-readable document name")
    required: bool = Field(
        default=False, description="Whether this document is mandatory for completion"
    )
    accepted_formats: list[str] = Field(
        default_factory=lambda: ["pdf", "csv", "xlsx"],
        description="Allowed file extensions (without leading dot)",
    )
    description: str = Field(default="", description="Instructions for applicant document upload")
    parser: str | None = Field(default=None, description="Optional specific parser identifier")


class WorkflowStageDefinition(BaseModel):
    id: str = Field(..., description="Stage identifier")
    label: str = Field(..., description="Human-readable stage label")
    description: str = Field(default="", description="Summary of what is collected at this stage")
    order: int = Field(default=0, description="Sequential stage order")


class WorkflowStateTransition(BaseModel):
    from_stage: str = Field(..., description="Current stage")
    to_stage: str = Field(..., description="Next stage when transition condition is satisfied")
    condition: Literal[
        "all_fields_present",
        "document_uploaded",
        "clarifications_resolved",
        "custom_rule",
    ] = Field(..., description="Condition type for transition")
    required_fields: list[str] = Field(default_factory=list, description="Fields that must exist")
    required_documents: list[str] = Field(
        default_factory=list, description="Document types that must exist"
    )
    summary: str = Field(default="", description="Audit summary recorded on transition")


class WorkflowDefinition(BaseModel):
    workflow_id: str = Field(..., description="Unique workflow identifier")
    workflow_version: int = Field(default=1, ge=1, description="Immutable integer workflow version")
    display_name: str = Field(..., description="Human-friendly workflow name")
    description: str = Field(..., description="Detailed description of the workflow purpose")
    category: str = Field(default="general", description="Industry or functional category")
    supported_languages: list[str] = Field(
        default_factory=lambda: ["en-IN", "ta-IN", "hi-IN"],
        description="BCP-47 language codes supported by this workflow",
    )
    input_modes: list[str] = Field(
        default_factory=lambda: ["audio", "text"],
        description="Allowed input modes",
    )
    stages: list[WorkflowStageDefinition] = Field(..., description="Ordered stage definitions")
    initial_stage: str = Field(..., description="ID of the starting stage")
    fields: list[WorkflowFieldDefinition] = Field(..., description="Field schema for the workflow")
    questions: list[WorkflowQuestionDefinition] = Field(..., description="Question templates")
    document_profiles: list[WorkflowDocumentProfile] = Field(
        default_factory=list, description="Document types accepted in this workflow"
    )
    transitions: list[WorkflowStateTransition] = Field(
        default_factory=list, description="Deterministic stage transition rules"
    )
    rules: list[str] = Field(
        default_factory=list,
        description="Domain rule plugin identifiers evaluated by this workflow",
    )
    completion_criteria: dict[str, Any] = Field(
        default_factory=dict, description="Criteria for applicant submission readiness"
    )
    human_review_required: bool = Field(
        default=True, description="Enforces that consequential actions require human review"
    )
    consent_version: str = Field(default="2026-v1", description="Consent policy version identifier")
    consent_notice: str = Field(
        default="I consent to the collection and processing of my declared facts for human review.",
        description="Consent and privacy notice text presented to the applicant",
    )
    feature_flags: dict[str, bool] = Field(
        default_factory=dict, description="Workflow-specific feature toggles"
    )

    @property
    def required_fields(self) -> list[str]:
        return [f.id for f in self.fields if f.required]

    @property
    def optional_fields(self) -> list[str]:
        return [f.id for f in self.fields if not f.required]

    @property
    def required_document_types(self) -> list[str]:
        return [d.id for d in self.document_profiles if d.required]

    @property
    def field_by_id(self) -> dict[str, WorkflowFieldDefinition]:
        return {f.id: f for f in self.fields}

    @property
    def question_by_id(self) -> dict[str, WorkflowQuestionDefinition]:
        return {q.id: q for q in self.questions}

    @property
    def question_by_field(self) -> dict[str, WorkflowQuestionDefinition]:
        return {q.field_key: q for q in self.questions}

    @property
    def stage_by_id(self) -> dict[str, WorkflowStageDefinition]:
        return {s.id: s for s in self.stages}

    def questions_for_stage(self, stage_id: str) -> list[WorkflowQuestionDefinition]:
        return sorted(
            [q for q in self.questions if q.stage == stage_id],
            key=lambda q: q.priority,
        )


class WorkflowSummary(BaseModel):
    workflow_id: str
    workflow_version: int
    display_name: str
    description: str
    category: str
    supported_languages: list[str]
    input_modes: list[str]
    required_field_count: int
    has_documents: bool
    human_review_required: bool
