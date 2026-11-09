from __future__ import annotations

from app.domain.provenance import (
    ALLOWED_FACT_TRANSITIONS,
    PROVENANCE_PRIORITY,
    ProvenanceStatus,
)


def test_provenance_priority_ordering():
    assert (
        PROVENANCE_PRIORITY[ProvenanceStatus.REVIEWER_VERIFIED]
        > PROVENANCE_PRIORITY[ProvenanceStatus.APPLICANT_CONFIRMED]
    )
    assert (
        PROVENANCE_PRIORITY[ProvenanceStatus.APPLICANT_CONFIRMED]
        > PROVENANCE_PRIORITY[ProvenanceStatus.CANDIDATE]
    )
    assert (
        ProvenanceStatus.APPLICANT_CONFIRMED in ALLOWED_FACT_TRANSITIONS[ProvenanceStatus.CANDIDATE]
    )
