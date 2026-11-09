from __future__ import annotations

try:
    from tests.helpers import (
        prepare_submitted_application,
        reviewer_headers,
    )
except ImportError:
    from helpers import (
        prepare_submitted_application,
        reviewer_headers,
    )


def test_complete_applicant_lifecycle(client):
    app_id, applicant_headers, uploaded = prepare_submitted_application(client)

    detail = client.get(f"/api/v1/applications/{app_id}", headers=applicant_headers)
    assert detail.status_code == 200
    assert detail.json()["application"]["status"] == "submitted_for_human_review"

    reviewer = reviewer_headers(client)
    packet = client.get(f"/api/v1/reviewer/applications/{app_id}", headers=reviewer)
    assert packet.status_code == 200
    assert packet.json()["application"]["id"] == app_id
