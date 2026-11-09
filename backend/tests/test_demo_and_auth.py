from __future__ import annotations

try:
    from tests.helpers import create_application, reviewer_headers
except ImportError:
    from helpers import create_application, reviewer_headers


def test_health_and_readiness(client):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] in {"ready", "degraded"}


def test_reviewer_session_lifecycle(client):
    created, applicant_headers = create_application(client)
    assert created["role"] == "applicant"

    me = client.get("/api/v1/sessions/me", headers=applicant_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "applicant"
    assert me.json()["application_id"] == created["application"]["id"]

    reviewer = reviewer_headers(client)
    reviewer_me = client.get("/api/v1/sessions/me", headers=reviewer)
    assert reviewer_me.status_code == 200
    assert reviewer_me.json()["role"] == "reviewer"

    logout = client.post("/api/v1/sessions/logout", headers=reviewer)
    assert logout.status_code == 200
    after_logout = client.get("/api/v1/sessions/me", headers=reviewer)
    assert after_logout.status_code == 401


def test_consent_and_reviewer_password_are_required(client):
    missing_consent = client.post(
        "/api/v1/applications",
        json={
            "applicant_name": "Test Applicant",
            "business_name": "Test Textiles",
            "language": "ta-IN",
            "voice": "Trisha",
            "consent_accepted": False,
        },
    )
    assert missing_consent.status_code == 422

    wrong_password = client.post(
        "/api/v1/sessions",
        json={
            "role": "reviewer",
            "email": "reviewer@kuralcredit.demo",
            "password": "wrong-password",
        },
    )
    assert wrong_password.status_code == 401
