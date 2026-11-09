from __future__ import annotations

from enum import StrEnum

from app.core.exceptions import InvalidStateTransition


class ApplicationStatus(StrEnum):
    CREATED = "created"
    CONSENT_PENDING = "consent_pending"
    COLLECTING_BUSINESS_CONTEXT = "collecting_business_context"
    COLLECTING_FINANCIAL_CONTEXT = "collecting_financial_context"
    COLLECTING_ISSUE_DETAILS = "collecting_issue_details"
    COLLECTING_TRIAGE_CONTEXT = "collecting_triage_context"
    COLLECTING_DOCUMENTS = "collecting_documents"
    RESOLVING_CLARIFICATIONS = "resolving_clarifications"
    APPLICANT_REVIEW = "applicant_review"
    SUBMITTED_FOR_HUMAN_REVIEW = "submitted_for_human_review"
    HUMAN_REVIEW_IN_PROGRESS = "human_review_in_progress"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    REVIEW_COMPLETED = "review_completed"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


ALLOWED_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.CREATED: frozenset(
        {ApplicationStatus.CONSENT_PENDING, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.CONSENT_PENDING: frozenset(
        {
            ApplicationStatus.COLLECTING_BUSINESS_CONTEXT,
            ApplicationStatus.COLLECTING_ISSUE_DETAILS,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.COLLECTING_BUSINESS_CONTEXT: frozenset(
        {ApplicationStatus.COLLECTING_FINANCIAL_CONTEXT, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.COLLECTING_FINANCIAL_CONTEXT: frozenset(
        {ApplicationStatus.COLLECTING_DOCUMENTS, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.COLLECTING_ISSUE_DETAILS: frozenset(
        {ApplicationStatus.COLLECTING_TRIAGE_CONTEXT, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.COLLECTING_TRIAGE_CONTEXT: frozenset(
        {
            ApplicationStatus.COLLECTING_DOCUMENTS,
            ApplicationStatus.RESOLVING_CLARIFICATIONS,
            ApplicationStatus.APPLICANT_REVIEW,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.COLLECTING_DOCUMENTS: frozenset(
        {
            ApplicationStatus.RESOLVING_CLARIFICATIONS,
            ApplicationStatus.APPLICANT_REVIEW,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.RESOLVING_CLARIFICATIONS: frozenset(
        {ApplicationStatus.APPLICANT_REVIEW, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.APPLICANT_REVIEW: frozenset(
        {
            ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
            ApplicationStatus.COLLECTING_DOCUMENTS,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW: frozenset(
        {ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS: frozenset(
        {
            ApplicationStatus.NEEDS_MORE_INFORMATION,
            ApplicationStatus.REVIEW_COMPLETED,
        }
    ),
    ApplicationStatus.NEEDS_MORE_INFORMATION: frozenset(
        {
            ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
            ApplicationStatus.WITHDRAWN,
        }
    ),
    ApplicationStatus.REVIEW_COMPLETED: frozenset({ApplicationStatus.ARCHIVED}),
    ApplicationStatus.WITHDRAWN: frozenset({ApplicationStatus.ARCHIVED}),
    ApplicationStatus.ARCHIVED: frozenset(),
}

ACTIVE_APPLICANT_STATUSES = frozenset(
    {
        ApplicationStatus.CREATED,
        ApplicationStatus.CONSENT_PENDING,
        ApplicationStatus.COLLECTING_BUSINESS_CONTEXT,
        ApplicationStatus.COLLECTING_FINANCIAL_CONTEXT,
        ApplicationStatus.COLLECTING_ISSUE_DETAILS,
        ApplicationStatus.COLLECTING_TRIAGE_CONTEXT,
        ApplicationStatus.COLLECTING_DOCUMENTS,
        ApplicationStatus.RESOLVING_CLARIFICATIONS,
        ApplicationStatus.APPLICANT_REVIEW,
        ApplicationStatus.NEEDS_MORE_INFORMATION,
    }
)

REVIEW_QUEUE_STATUSES = frozenset(
    {
        ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
        ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS,
        ApplicationStatus.NEEDS_MORE_INFORMATION,
        ApplicationStatus.REVIEW_COMPLETED,
    }
)


def can_transition(current: ApplicationStatus | str, target: ApplicationStatus | str) -> bool:
    current_status = ApplicationStatus(current)
    target_status = ApplicationStatus(target)
    if current_status == target_status:
        return True
    return target_status in ALLOWED_TRANSITIONS[current_status]


def assert_transition(
    current: ApplicationStatus | str, target: ApplicationStatus | str
) -> ApplicationStatus:
    current_status = ApplicationStatus(current)
    target_status = ApplicationStatus(target)
    if not can_transition(current_status, target_status):
        raise InvalidStateTransition(
            f"Cannot move application from '{current_status}' to '{target_status}'"
        )
    return target_status
