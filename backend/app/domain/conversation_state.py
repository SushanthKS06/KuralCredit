from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.lifecycle import ApplicationStatus


class ConversationStage(StrEnum):
    BUSINESS_CONTEXT = "collecting_business_context"
    FINANCIAL_CONTEXT = "collecting_financial_context"
    ISSUE_DETAILS = "collecting_issue_details"
    TRIAGE_CONTEXT = "collecting_triage_context"
    DOCUMENTS = "collecting_documents"
    CLARIFICATIONS = "resolving_clarifications"
    APPLICANT_REVIEW = "applicant_review"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    SUBMITTED = "submitted_for_human_review"
    CLOSED = "closed"


STAGE_BY_STATUS = {
    ApplicationStatus.COLLECTING_BUSINESS_CONTEXT: ConversationStage.BUSINESS_CONTEXT,
    ApplicationStatus.COLLECTING_FINANCIAL_CONTEXT: ConversationStage.FINANCIAL_CONTEXT,
    ApplicationStatus.COLLECTING_ISSUE_DETAILS: ConversationStage.ISSUE_DETAILS,
    ApplicationStatus.COLLECTING_TRIAGE_CONTEXT: ConversationStage.TRIAGE_CONTEXT,
    ApplicationStatus.COLLECTING_DOCUMENTS: ConversationStage.DOCUMENTS,
    ApplicationStatus.RESOLVING_CLARIFICATIONS: ConversationStage.CLARIFICATIONS,
    ApplicationStatus.APPLICANT_REVIEW: ConversationStage.APPLICANT_REVIEW,
    ApplicationStatus.NEEDS_MORE_INFORMATION: ConversationStage.NEEDS_MORE_INFORMATION,
    ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW: ConversationStage.SUBMITTED,
    ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS: ConversationStage.SUBMITTED,
    ApplicationStatus.REVIEW_COMPLETED: ConversationStage.CLOSED,
    ApplicationStatus.WITHDRAWN: ConversationStage.CLOSED,
    ApplicationStatus.ARCHIVED: ConversationStage.CLOSED,
}


@dataclass(frozen=True)
class WorkflowQuestion:
    question_id: str
    field_key: str
    stage: ConversationStage
    prompt: str
    reason: str
    expected_answer_type: str
    priority: int


WORKFLOW_QUESTIONS: tuple[WorkflowQuestion, ...] = (
    WorkflowQuestion(
        question_id="q_business_type",
        field_key="business_type",
        stage=ConversationStage.BUSINESS_CONTEXT,
        prompt="What kind of business do you run, and what do you mainly sell?",
        reason="A reviewer needs to understand the business before reading its financial records.",
        expected_answer_type="text",
        priority=10,
    ),
    WorkflowQuestion(
        question_id="q_years_in_operation",
        field_key="years_in_operation",
        stage=ConversationStage.BUSINESS_CONTEXT,
        prompt="How many years has the business been operating?",
        reason="Business age helps a reviewer interpret the records in context.",
        expected_answer_type="number",
        priority=20,
    ),
    WorkflowQuestion(
        question_id="q_annual_sales",
        field_key="annual_sales",
        stage=ConversationStage.FINANCIAL_CONTEXT,
        prompt=(
            "What were your total sales in the last financial year, April 2025 to March 2026? "
            "You can say an amount like 18 lakh."
        ),
        reason=(
            "Declared sales are compared with GST turnover and bank records using explicit rules."
        ),
        expected_answer_type="amount",
        priority=30,
    ),
    WorkflowQuestion(
        question_id="q_gst_turnover",
        field_key="gst_turnover",
        stage=ConversationStage.FINANCIAL_CONTEXT,
        prompt="What turnover was reported in your GST returns for the same year?",
        reason="GST turnover is a separate measure and may differ from total sales.",
        expected_answer_type="amount",
        priority=40,
    ),
    WorkflowQuestion(
        question_id="q_bank_statement",
        field_key="bank_statement",
        stage=ConversationStage.DOCUMENTS,
        prompt=(
            "Please upload a bank statement for the same period. CSV, XLSX, or a text-based "
            "PDF is supported."
        ),
        reason=("Bank credits help a reviewer compare records and are not treated as revenue."),
        expected_answer_type="document",
        priority=50,
    ),
)

QUESTION_BY_ID = {question.question_id: question for question in WORKFLOW_QUESTIONS}
QUESTION_BY_FIELD = {question.field_key: question for question in WORKFLOW_QUESTIONS}


def stage_for_status(status: ApplicationStatus | str) -> ConversationStage:
    return STAGE_BY_STATUS.get(ApplicationStatus(status), ConversationStage.CLOSED)


def questions_for_stage(stage: ConversationStage) -> list[WorkflowQuestion]:
    return sorted(
        [question for question in WORKFLOW_QUESTIONS if question.stage == stage],
        key=lambda question: question.priority,
    )
