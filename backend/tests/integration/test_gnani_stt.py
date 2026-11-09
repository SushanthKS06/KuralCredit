from __future__ import annotations

try:
    from tests.helpers import create_application, wav_bytes
except ImportError:
    from helpers import create_application, wav_bytes


def test_stt_transcription_endpoint(client):
    created, headers = create_application(client, language="ta-IN")
    app_id = created["application"]["id"]

    transcribed = client.post(
        "/api/v1/speech/transcribe",
        headers=headers,
        data={"application_id": app_id, "language": "ta-IN"},
        files={"audio": ("sample.wav", wav_bytes(), "audio/wav")},
    )
    assert transcribed.status_code == 200, transcribed.text
    body = transcribed.json()
    assert body["transcript"]
    assert body["language"] == "ta-IN"
