from __future__ import annotations


def test_workflow_discovery_endpoint(client):
    res = client.get("/api/v1/workflows")
    assert res.status_code == 200
    workflows = res.json()
    assert isinstance(workflows, list)
    ids = {w["workflow_id"] for w in workflows}
    assert "loan_application" in ids
    assert "customer_support_intake" in ids

    # Detail query for loan application
    loan_res = client.get("/api/v1/workflows/loan_application")
    assert loan_res.status_code == 200
    loan_wf = loan_res.json()
    assert loan_wf["workflow_id"] == "loan_application"
    assert loan_wf["category"] == "lending"
    assert "annual_sales" in [f["id"] for f in loan_wf["fields"]]

    # Detail query for customer support intake
    support_res = client.get("/api/v1/workflows/customer_support_intake")
    assert support_res.status_code == 200
    support_wf = support_res.json()
    assert support_wf["workflow_id"] == "customer_support_intake"
    assert support_wf["category"] == "customer_support"
    assert "customer_issue" in [f["id"] for f in support_wf["fields"]]


def test_customer_support_workflow_end_to_end(client):
    """Proves the generic conversation engine executes a non-loan workflow.

    Runs customer support ticket intake and triage through the exact same
    conversation service, fact extraction, and human review pipeline without
    any hardcoded loan dependencies.
    """
    # 1. Create a session for customer_support_intake
    create_payload = {
        "workflow_id": "customer_support_intake",
        "applicant_name": "Arun Kumar",
        "business_name": "N/A - Retail Customer",
        "language": "en-IN",
        "voice": "Kaveri",
        "consent_accepted": True,
        "consent_version": "2026-support-v1",
    }
    res = client.post("/api/v1/applications", json=create_payload)
    assert res.status_code == 201, res.text
    body = res.json()
    app_id = body["application"]["id"]
    token = body["token"]
    assert body["application"]["workflow_id"] == "customer_support_intake"
    assert body["application"]["workflow_version"] == 1
    assert body["application"]["status"] == "collecting_issue_details"
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial question from the workflow
    conv_res = client.get(f"/api/v1/applications/{app_id}/conversation", headers=headers)
    assert conv_res.status_code == 200
    conv = conv_res.json()
    assert conv["status"] == "collecting_issue_details"
    assert conv["next_question"] is not None
    assert conv["next_question"]["question_id"] == "q_customer_issue"
    assert conv["next_question"]["field_key"] == "customer_issue"

    # 3. Answer question 1: customer_issue
    turn_1 = client.post(
        f"/api/v1/applications/{app_id}/conversation/turns",
        headers=headers,
        json={
            "text": "The service fails with timeout error 504 on checkout.",
            "language": "en-IN",
            "input_mode": "text",
        },
    )
    assert turn_1.status_code == 200, turn_1.text
    turn_1_body = turn_1.json()
    assert turn_1_body["facts_created"] >= 1
    assert "customer_issue" in turn_1_body["candidate_field_keys"]

    # Next question should be product_or_service
    assert turn_1_body["next_question"] is not None
    assert turn_1_body["next_question"]["question_id"] == "q_product_or_service"
    assert turn_1_body["next_question"]["field_key"] == "product_or_service"

    # 4. Answer question 2: product_or_service
    turn_2 = client.post(
        f"/api/v1/applications/{app_id}/conversation/turns",
        headers=headers,
        json={
            "text": "This is regarding the Payment Gateway API Pro subscription.",
            "language": "en-IN",
            "input_mode": "text",
        },
    )
    assert turn_2.status_code == 200, turn_2.text
    turn_2_body = turn_2.json()
    assert "product_or_service" in turn_2_body["candidate_field_keys"]

    # The workflow should have transitioned stage from
    # collecting_issue_details to collecting_triage_context
    assert turn_2_body["conversation"]["status"] == "collecting_triage_context"
    assert turn_2_body["next_question"]["question_id"] == "q_urgency"

    # 5. Answer question 3: urgency
    turn_3 = client.post(
        f"/api/v1/applications/{app_id}/conversation/turns",
        headers=headers,
        json={
            "text": "This issue is high urgency because checkouts are blocked.",
            "language": "en-IN",
            "input_mode": "text",
        },
    )
    assert turn_3.status_code == 200, turn_3.text
    turn_3_body = turn_3.json()
    assert "urgency" in turn_3_body["candidate_field_keys"]
    assert turn_3_body["next_question"]["question_id"] == "q_preferred_contact_method"

    # 6. Answer question 4: preferred_contact_method
    turn_4 = client.post(
        f"/api/v1/applications/{app_id}/conversation/turns",
        headers=headers,
        json={
            "text": "Please reach me via phone for fastest resolution.",
            "language": "en-IN",
            "input_mode": "text",
        },
    )
    assert turn_4.status_code == 200, turn_4.text
    turn_4_body = turn_4.json()
    assert "preferred_contact_method" in turn_4_body["candidate_field_keys"]

    # 7. Check facts and confirm them
    facts_res = client.get(f"/api/v1/applications/{app_id}/facts", headers=headers)
    assert facts_res.status_code == 200
    facts_data = facts_res.json()["items"]
    fact_keys = {f["field_key"]: f["id"] for f in facts_data}
    assert "customer_issue" in fact_keys
    assert "product_or_service" in fact_keys
    assert "urgency" in fact_keys
    assert "preferred_contact_method" in fact_keys

    for fact_id in fact_keys.values():
        conf_res = client.post(
            f"/api/v1/facts/{fact_id}/corrections",
            headers=headers,
            json={"action": "confirm"},
        )
        assert conf_res.status_code == 200

    # 8. Check completeness of support ticket
    comp_res = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert comp_res.status_code == 200
    comp_body = comp_res.json()["completeness"]
    assert comp_body["can_submit"] is True
    assert len(comp_body["missing_fields"]) == 0
    assert len(comp_body["unconfirmed_fields"]) == 0

    # 9. Submit for human review
    submit_res = client.post(
        f"/api/v1/applications/{app_id}/submit",
        headers=headers,
        json={"confirm_accuracy": True, "acknowledge_no_decision": True},
    )
    assert submit_res.status_code == 200, submit_res.text
    submit_body = submit_res.json()
    assert submit_body["application"]["status"] == "submitted_for_human_review"
