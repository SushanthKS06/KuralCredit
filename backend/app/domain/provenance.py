from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    APPLICANT_SPEECH = "applicant_speech"
    APPLICANT_TEXT = "applicant_text"
    BANK_STATEMENT = "bank_statement"
    GST_DOCUMENT = "GST_document"
    SALES_REGISTER = "sales_register"
    OTHER_DOCUMENT = "other_document"
    REVIEWER = "reviewer"
    SYSTEM = "system"


class ProvenanceStatus(StrEnum):
    CANDIDATE = "candidate"
    APPLICANT_CONFIRMED = "applicant_confirmed"
    DOCUMENT_EXTRACTED = "document_extracted"
    REVIEWER_VERIFIED = "reviewer_verified"
    REJECTED = "rejected"


class ExtractionMethod(StrEnum):
    RULE_BASED = "rule_based"
    MODEL_ASSISTED = "model_assisted"
    APPLICANT_ENTERED = "applicant_entered"
    REVIEWER_ENTERED = "reviewer_entered"
    DOCUMENT_PARSER = "document_parser"


PROVENANCE_PRIORITY: dict[ProvenanceStatus, int] = {
    ProvenanceStatus.REVIEWER_VERIFIED: 5,
    ProvenanceStatus.APPLICANT_CONFIRMED: 4,
    ProvenanceStatus.DOCUMENT_EXTRACTED: 3,
    ProvenanceStatus.CANDIDATE: 2,
    ProvenanceStatus.REJECTED: 0,
}

ALLOWED_FACT_TRANSITIONS: dict[ProvenanceStatus, frozenset[ProvenanceStatus]] = {
    ProvenanceStatus.CANDIDATE: frozenset(
        {
            ProvenanceStatus.APPLICANT_CONFIRMED,
            ProvenanceStatus.REJECTED,
            ProvenanceStatus.REVIEWER_VERIFIED,
        }
    ),
    ProvenanceStatus.DOCUMENT_EXTRACTED: frozenset(
        {
            ProvenanceStatus.APPLICANT_CONFIRMED,
            ProvenanceStatus.REJECTED,
            ProvenanceStatus.REVIEWER_VERIFIED,
        }
    ),
    ProvenanceStatus.APPLICANT_CONFIRMED: frozenset(
        {ProvenanceStatus.REVIEWER_VERIFIED, ProvenanceStatus.REJECTED}
    ),
    ProvenanceStatus.REVIEWER_VERIFIED: frozenset(),
    ProvenanceStatus.REJECTED: frozenset(),
}


def can_transition_fact(current: ProvenanceStatus | str, target: ProvenanceStatus | str) -> bool:
    current_status = ProvenanceStatus(current)
    target_status = ProvenanceStatus(target)
    if current_status == target_status:
        return True
    return target_status in ALLOWED_FACT_TRANSITIONS[current_status]


def is_confirmed(status: ProvenanceStatus | str) -> bool:
    return ProvenanceStatus(status) in {
        ProvenanceStatus.APPLICANT_CONFIRMED,
        ProvenanceStatus.REVIEWER_VERIFIED,
    }


def is_active(status: ProvenanceStatus | str) -> bool:
    return ProvenanceStatus(status) != ProvenanceStatus.REJECTED
