from __future__ import annotations

try:
    from tests.helpers import create_application, upload_bank_statement, wav_bytes
except ImportError:
    from helpers import create_application, upload_bank_statement, wav_bytes


def test_speech_transcription_and_synthesis(client):
    created, headers = create_application(client, language="en-IN")
    app_id = created["application"]["id"]

    status = client.get("/api/v1/speech/status")
    assert status.status_code == 200
    assert status.json()["stt_available"] is True
    assert status.json()["tts_available"] is True

    transcribed = client.post(
        "/api/v1/speech/transcribe",
        headers=headers,
        data={"application_id": app_id, "language": "en-IN"},
        files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
    )
    assert transcribed.status_code == 200, transcribed.text
    assert "18 lakh" in transcribed.json()["transcript"]

    synthesized = client.post(
        "/api/v1/speech/synthesize",
        headers=headers,
        json={
            "application_id": app_id,
            "text": "What were your sales last year?",
            "language": "en-IN",
            "voice": "Kaveri",
        },
    )
    assert synthesized.status_code == 200, synthesized.text
    assert synthesized.headers["content-type"].startswith("audio/wav")
    assert synthesized.content.startswith(b"RIFF")


def test_speech_rejects_audio_over_provider_limit(client):
    created, headers = create_application(client, language="en-IN")
    app_id = created["application"]["id"]

    response = client.post(
        "/api/v1/speech/transcribe",
        headers=headers,
        data={"application_id": app_id, "language": "en-IN"},
        files={"audio": ("answer.wav", wav_bytes(seconds=31), "audio/wav")},
    )

    assert response.status_code == 422
    assert "at most 30 seconds" in response.text


def test_speech_rejects_blank_synthesis_text(client):
    created, headers = create_application(client, language="en-IN")
    app_id = created["application"]["id"]

    response = client.post(
        "/api/v1/speech/synthesize",
        headers=headers,
        json={
            "application_id": app_id,
            "text": "   ",
            "language": "en-IN",
            "voice": "Kaveri",
        },
    )

    assert response.status_code == 422


def test_document_file_download_and_applicant_isolation(client):
    created, headers = create_application(client)
    app_id = created["application"]["id"]
    uploaded = upload_bank_statement(client, app_id, headers)
    document_id = uploaded["document"]["id"]

    downloaded = client.get(f"/api/v1/documents/{document_id}/file", headers=headers)
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"].startswith("text/csv")
    assert b"Opening customer receipts" in downloaded.content

    other, other_headers = create_application(client)
    forbidden = client.get(f"/api/v1/documents/{document_id}/file", headers=other_headers)
    assert forbidden.status_code == 403
    assert other["application"]["id"] != app_id

    unauthenticated = client.get(f"/api/v1/documents/{document_id}/file")
    assert unauthenticated.status_code == 401
