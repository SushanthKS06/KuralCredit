from __future__ import annotations


def test_api_health_contract(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body
    assert "version" in body
    assert "database" in body
    assert "providers" in body


def test_api_capabilities_contract(client):
    res = client.get("/api/v1/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert "languages" in body
    assert "defaults" in body
    assert len(body["languages"]) > 0
    assert body["stt_max_audio_seconds"] == 30
    assert "wav" in body["stt_supported_formats"]
    assert body["stt_max_upload_bytes"] > 0
    assert "wav" in body["tts_supported_formats"]
    assert body["providers"]["provider_mode"] == "real"
    assert body["providers"]["mock_mode"] is False
    assert body["providers"]["live_provider_calls"] is True
