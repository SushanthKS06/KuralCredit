from __future__ import annotations

from app.core.lifecycle import (
    ACTIVE_APPLICANT_STATUSES,
    ALLOWED_TRANSITIONS,
    REVIEW_QUEUE_STATUSES,
    ApplicationStatus,
    assert_transition,
    can_transition,
)

EDITABLE_APPLICANT_STATUSES = frozenset(
    {
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

FINAL_STATUSES = frozenset(
    {
        ApplicationStatus.REVIEW_COMPLETED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.ARCHIVED,
    }
)


def is_editable_by_applicant(status: ApplicationStatus | str) -> bool:
    return ApplicationStatus(status) in EDITABLE_APPLICANT_STATUSES


def is_active(status: ApplicationStatus | str) -> bool:
    return ApplicationStatus(status) in ACTIVE_APPLICANT_STATUSES


def is_in_review_queue(status: ApplicationStatus | str) -> bool:
    return ApplicationStatus(status) in REVIEW_QUEUE_STATUSES


def is_final(status: ApplicationStatus | str) -> bool:
    return ApplicationStatus(status) in FINAL_STATUSES


__all__ = [
    "ALLOWED_TRANSITIONS",
    "ApplicationStatus",
    "assert_transition",
    "can_transition",
    "is_active",
    "is_editable_by_applicant",
    "is_final",
    "is_in_review_queue",
]
