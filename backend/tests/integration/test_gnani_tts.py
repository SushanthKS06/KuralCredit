from __future__ import annotations

try:
    from tests.helpers import create_application
except ImportError:
    from helpers import create_application


def test_tts_synthesis_endpoint(client):
    created, headers = create_application(client, language="ta-IN", voice="Trisha")
    app_id = created["application"]["id"]

    synthesized = client.post(
        "/api/v1/speech/synthesize",
        headers=headers,
        json={
            "application_id": app_id,
            "text": "வணக்கம், உங்கள் வருடாந்திர விற்பனை எவ்வளவு?",
            "language": "ta-IN",
            "voice": "Trisha",
        },
    )
    assert synthesized.status_code == 200, synthesized.text
    assert synthesized.headers["content-type"].startswith("audio/wav")
    assert synthesized.content.startswith(b"RIFF")
