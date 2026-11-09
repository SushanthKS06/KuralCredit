from __future__ import annotations

try:
    from tests.helpers import create_application, submit_text_turn
except ImportError:
    from helpers import create_application, submit_text_turn


def test_groq_reasoning_fact_extraction(client):
    created, headers = create_application(client)
    app_id = created["application"]["id"]

    turn = submit_text_turn(
        client,
        app_id,
        headers,
        "Last year sales were 18 lakh rupees. GST turnover was 16 lakh 50 thousand.",
    )
    assert turn["facts_created"] >= 2
    assert "annual_sales" in turn["candidate_field_keys"]
