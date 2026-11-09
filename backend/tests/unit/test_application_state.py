from __future__ import annotations

import pytest

from app.core.exceptions import InvalidStateTransition
from app.core.lifecycle import ApplicationStatus, assert_transition, can_transition


def test_allowed_state_transitions():
    assert can_transition(ApplicationStatus.CREATED, ApplicationStatus.CONSENT_PENDING) is True
    assert (
        can_transition(
            ApplicationStatus.CONSENT_PENDING,
            ApplicationStatus.COLLECTING_BUSINESS_CONTEXT,
        )
        is True
    )
    assert (
        can_transition(
            ApplicationStatus.SUBMITTED_FOR_HUMAN_REVIEW,
            ApplicationStatus.HUMAN_REVIEW_IN_PROGRESS,
        )
        is True
    )


def test_forbidden_state_transitions():
    assert can_transition(ApplicationStatus.CREATED, ApplicationStatus.REVIEW_COMPLETED) is False
    assert can_transition(ApplicationStatus.REVIEW_COMPLETED, ApplicationStatus.CREATED) is False

    with pytest.raises(InvalidStateTransition):
        assert_transition(ApplicationStatus.CREATED, ApplicationStatus.REVIEW_COMPLETED)
