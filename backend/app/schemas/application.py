from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import CONSENT_VERSION


class ApplicationCreate(BaseModel):
    workflow_id: str = "loan_application"
    applicant_name: str = Field(min_length=2, max_length=120)
    business_name: str = Field(min_length=2, max_length=160)
    language: str = Field(min_length=2, max_length=20)
    voice: str = Field(min_length=2, max_length=60)
    consent_accepted: bool
    consent_version: str = CONSENT_VERSION

    @model_validator(mode="after")
    def require_consent(self) -> ApplicationCreate:
        if not self.consent_accepted:
            raise ValueError("Explicit consent is required before creating an application")
        return self


class ApplicationUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=160)
    business_type: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, min_length=2, max_length=20)
    voice: str | None = Field(default=None, min_length=2, max_length=60)


class ConsentRequest(BaseModel):
    consent_accepted: bool
    consent_version: str = CONSENT_VERSION

    @model_validator(mode="after")
    def require_consent(self) -> ConsentRequest:
        if not self.consent_accepted:
            raise ValueError("Consent must be accepted")
        return self


class CompletenessItem(BaseModel):
    key: str
    label: str
    complete: bool
    detail: str


class CompletenessOut(BaseModel):
    can_submit: bool
    missing_fields: list[str]
    unconfirmed_fields: list[str]
    missing_documents: list[str]
    open_clarifications: int
    items: list[CompletenessItem]


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    reference: str
    workflow_id: str = "loan_application"
    workflow_version: int = 1
    status: str
    applicant_name: str
    business_name: str
    business_type: str | None
    language: str
    voice: str
    consent_version: str | None
    consent_given_at: datetime | None
    submitted_at: datetime | None
    review_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_demo: bool
    demo_scenario: str | None


class ApplicationDetailOut(BaseModel):
    application: ApplicationOut
    completeness: CompletenessOut


class ApplicationCreatedOut(BaseModel):
    application: ApplicationOut
    completeness: CompletenessOut
    token: str
    session_id: str
    role: str = "applicant"
    expires_at: datetime


class ApplicationListOut(BaseModel):
    items: list[ApplicationOut]
    total: int


class SubmitRequest(BaseModel):
    confirm_accuracy: bool
    acknowledge_no_decision: bool

    @model_validator(mode="after")
    def require_acknowledgements(self) -> SubmitRequest:
        if not self.confirm_accuracy:
            raise ValueError("Applicant must confirm the application summary")
        if not self.acknowledge_no_decision:
            raise ValueError("Applicant must acknowledge that KuralCredit makes no credit decision")
        return self


class SubmitResponse(BaseModel):
    application: ApplicationOut
    message: str


class WithdrawRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class DeleteResponse(BaseModel):
    message: str
    deleted_application_id: str


class ApplicantProfileOut(BaseModel):
    application_id: str
    applicant_name: str
    business_name: str
    business_type: str | None
    language: str
    voice: str
    status: str
    next_action: Literal[
        "consent",
        "interview",
        "documents",
        "clarifications",
        "review",
        "submitted",
        "withdrawn",
        "complete",
    ]
