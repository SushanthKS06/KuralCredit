from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

if sys.platform == "win32":
    import asyncio

    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

os.environ["APP_ENV"] = "development"
os.environ["GNANI_API_KEY"] = "test-gnani-key"
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["SECRET_KEY"] = "test-secret-key-long-enough-for-hs256"
os.environ["REVIEWER_DEMO_EMAIL"] = "reviewer@kuralcredit.demo"
os.environ["REVIEWER_DEMO_PASSWORD"] = "test-reviewer-password"
os.environ["RATE_LIMIT_PER_MINUTE"] = "600"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from fastapi.testclient import TestClient

    from app.api.deps import get_registry_dep
    from app.core.config import get_settings
    from app.db.session import reset_engine
    from app.providers.registry import get_catalog, reset_registry
    from tests.fakes.providers import build_fake_registry

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    reset_registry()
    reset_engine()

    from app.main import app

    fake_registry = build_fake_registry(get_settings(), get_catalog())
    app.dependency_overrides[get_registry_dep] = lambda: fake_registry

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_registry_dep, None)
    reset_engine()
    get_settings.cache_clear()
    reset_registry()
