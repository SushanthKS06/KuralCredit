from __future__ import annotations

try:
    from tests.helpers import (
        answer_open_clarifications,
        confirm_all_facts,
        create_application,
        prepare_submitted_application,
        reviewer_headers,
        submit_application,
        submit_text_turn,
        upload_bank_statement,
    )
except ImportError:
    from helpers import (
        answer_open_clarifications,
        confirm_all_facts,
        create_application,
        prepare_submitted_application,
        reviewer_headers,
        submit_application,
        submit_text_turn,
        upload_bank_statement,
    )


def test_full_applicant_and_reviewer_flow(client):
    app_id, applicant_headers, uploaded = prepare_submitted_application(client)

    detail = client.get(f"/api/v1/applications/{app_id}", headers=applicant_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["application"]["status"] == "submitted_for_human_review"
    assert detail.json()["completeness"]["missing_fields"] == []
    assert detail.json()["completeness"]["unconfirmed_fields"] == []
    assert detail.json()["completeness"]["open_clarifications"] == 0

    applicant_queue = client.get("/api/v1/reviewer/queue", headers=applicant_headers)
    assert applicant_queue.status_code == 403

    reviewer = reviewer_headers(client)
    queue = client.get("/api/v1/reviewer/queue", headers=reviewer)
    assert queue.status_code == 200, queue.text
    assert queue.json()["total"] == 1
    assert queue.json()["items"][0]["application_id"] == app_id
    assert queue.json()["items"][0]["completeness_percent"] == 100

    reviewer_detail = client.get(f"/api/v1/reviewer/applications/{app_id}", headers=reviewer)
    assert reviewer_detail.status_code == 200, reviewer_detail.text
    body = reviewer_detail.json()
    assert "does not approve" in body["boundary_notice"]
    assert body["summary"]["limitations"]
    assert body["documents"][0]["id"] == uploaded["document"]["id"]

    exported = client.get(f"/api/v1/reviewer/applications/{app_id}/export", headers=reviewer)
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-disposition"].startswith("attachment;")
    assert exported.json()["application"]["id"] == app_id
    assert exported.json()["boundary_notice"]

    verified = client.post(
        f"/api/v1/reviewer/applications/{app_id}/actions",
        headers={**reviewer, "Idempotency-Key": "verify-annual-sales"},
        json={
            "action": "verify_fact",
            "field_key": "annual_sales",
            "reason": "Reviewed against the applicant statement and bank statement.",
        },
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["action"] == "verify_fact"

    replay = client.post(
        f"/api/v1/reviewer/applications/{app_id}/actions",
        headers={**reviewer, "Idempotency-Key": "verify-annual-sales"},
        json={
            "action": "verify_fact",
            "field_key": "annual_sales",
            "reason": "Reviewed against the applicant statement and bank statement.",
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.headers["Idempotent-Replay"] == "true"

    requested = client.post(
        f"/api/v1/reviewer/applications/{app_id}/actions",
        headers=reviewer,
        json={
            "action": "request_information",
            "field_key": "gst_turnover",
            "reason": "Please explain the difference between GST turnover and declared sales.",
        },
    )
    assert requested.status_code == 200, requested.text

    conversation = client.get(
        f"/api/v1/applications/{app_id}/conversation", headers=applicant_headers
    )
    assert conversation.status_code == 200, conversation.text
    assert conversation.json()["status"] == "needs_more_information"
    assert conversation.json()["open_clarifications"]

    answer_open_clarifications(client, app_id, applicant_headers)
    resubmitted = submit_application(client, app_id, applicant_headers)
    assert resubmitted.json()["application"]["status"] == "submitted_for_human_review"

    completed = client.post(
        f"/api/v1/reviewer/applications/{app_id}/actions",
        headers=reviewer,
        json={
            "action": "complete_review",
            "reason": "Applicant explanations and evidence reviewed by a human.",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["action"] == "complete_review"

    final = client.get(f"/api/v1/applications/{app_id}", headers=applicant_headers)
    assert final.json()["application"]["status"] == "review_completed"


def test_submit_idempotency_replays_original_response(client):
    created, headers = create_application(client)
    app_id = created["application"]["id"]
    submit_text_turn(
        client,
        app_id,
        headers,
        "My business is a textile shop. Last year sales were 18 lakh rupees. "
        "GST turnover was 16 lakh 50 thousand.",
    )
    confirm_all_facts(client, app_id, headers)
    upload_bank_statement(client, app_id, headers)
    answer_open_clarifications(client, app_id, headers)
    confirm_all_facts(client, app_id, headers)

    idempotent_headers = {**headers, "Idempotency-Key": "submit-once"}
    first = submit_application(client, app_id, headers, **{"Idempotency-Key": "submit-once"})
    second = client.post(
        f"/api/v1/applications/{app_id}/submit",
        headers=idempotent_headers,
        json={"confirm_accuracy": True, "acknowledge_no_decision": True},
    )
    assert second.status_code == 200, second.text
    assert second.headers["Idempotent-Replay"] == "true"
    assert second.json()["application"]["id"] == first.json()["application"]["id"]
