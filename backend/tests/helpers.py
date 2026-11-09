from __future__ import annotations

import io
import wave

BANK_CSV = (
    b"Date,Description,Credit,Debit\n"
    b"01/04/2025,Opening customer receipts,400000,\n"
    b"15/05/2025,Customer receipts,350000,\n"
    b"10/06/2025,Customer receipts,300000,\n"
    b"12/07/2025,Customer receipts,250000,\n"
    b"20/08/2025,Customer receipts,200000,\n"
    b"18/09/2025,Customer receipts,250000,\n"
    b"05/10/2025,Customer receipts,300000,\n"
    b"14/11/2025,Customer receipts,250000,\n"
    b"09/12/2025,Customer receipts,200000,\n"
    b"22/01/2026,Customer receipts,200000,\n"
    b"11/02/2026,Customer receipts,150000,\n"
    b"20/03/2026,Customer receipts,150000,\n"
)

APPLICANT_TEXT = (
    "My business is a textile shop. Last year sales were 18 lakh rupees. "
    "GST turnover was 16 lakh 50 thousand."
)
CLARIFICATION_ANSWER = (
    "Some bank credits were transfers from my own account and customer receipts. "
    "Part of the sales were cash recorded in my sales register."
)
DEFAULT_VOICES = {"en-IN": "Kaveri", "ta-IN": "Trisha"}


def wav_bytes(seconds: float = 1.0) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buffer.getvalue()


def create_application(client, *, language: str = "ta-IN", voice: str | None = None):
    selected_voice = voice or DEFAULT_VOICES.get(language, "Trisha")
    response = client.post(
        "/api/v1/applications",
        json={
            "applicant_name": "Test Applicant",
            "business_name": "Test Textiles",
            "language": language,
            "voice": selected_voice,
            "consent_accepted": True,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    headers = {"Authorization": f"Bearer {data['token']}"}
    return data, headers


def submit_text_turn(client, app_id: str, headers: dict[str, str], text: str):
    response = client.post(
        f"/api/v1/applications/{app_id}/conversation/turns",
        headers=headers,
        json={"text": text, "input_mode": "text"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def confirm_all_facts(client, app_id: str, headers: dict[str, str]) -> list[dict]:
    response = client.get(f"/api/v1/applications/{app_id}/facts", headers=headers)
    assert response.status_code == 200, response.text
    facts = response.json()["items"]
    for fact in facts:
        if fact["provenance_status"] in {"candidate", "document_extracted"}:
            confirm = client.post(
                f"/api/v1/facts/{fact['id']}/corrections",
                headers=headers,
                json={"action": "confirm"},
            )
            assert confirm.status_code == 200, confirm.text
    return facts


def upload_bank_statement(client, app_id: str, headers: dict[str, str]):
    response = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=headers,
        data={"document_type": "bank_statement"},
        files={"file": ("bank.csv", BANK_CSV, "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def answer_open_clarifications(client, app_id: str, headers: dict[str, str]) -> None:
    for _ in range(8):
        response = client.get(f"/api/v1/applications/{app_id}/conversation", headers=headers)
        assert response.status_code == 200, response.text
        conversation = response.json()
        if not conversation["open_clarifications"]:
            return
        clarification = conversation["open_clarifications"][0]
        answer = client.post(
            f"/api/v1/applications/{app_id}/conversation/turns",
            headers=headers,
            json={
                "text": CLARIFICATION_ANSWER,
                "input_mode": "text",
                "clarification_id": clarification["id"],
            },
        )
        assert answer.status_code == 200, answer.text
    raise AssertionError("Clarifications did not converge")


def submit_application(client, app_id: str, headers: dict[str, str], **extra_headers):
    response = client.post(
        f"/api/v1/applications/{app_id}/submit",
        headers={**headers, **extra_headers},
        json={"confirm_accuracy": True, "acknowledge_no_decision": True},
    )
    assert response.status_code == 200, response.text
    return response


def prepare_submitted_application(client):
    created, headers = create_application(client)
    app_id = created["application"]["id"]
    submit_text_turn(client, app_id, headers, APPLICANT_TEXT)
    confirm_all_facts(client, app_id, headers)
    uploaded = upload_bank_statement(client, app_id, headers)
    answer_open_clarifications(client, app_id, headers)
    confirm_all_facts(client, app_id, headers)
    submit_application(client, app_id, headers)
    return app_id, headers, uploaded


def reviewer_headers(client) -> dict[str, str]:
    response = client.post(
        "/api/v1/sessions",
        json={
            "role": "reviewer",
            "email": "reviewer@kuralcredit.demo",
            "password": "test-reviewer-password",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}
