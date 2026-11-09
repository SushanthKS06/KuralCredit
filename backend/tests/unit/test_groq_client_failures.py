from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderSchemaError,
    ProviderTimeoutError,
)
from app.providers.groq.client import GroqClient


class _Schema(BaseModel):
    value: str


class _StubResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers: dict[str, str] = {}

    def json(self) -> dict:
        return self._payload


class _StubClient:
    calls: list[dict] = []
    response: _StubResponse | Exception = _StubResponse(200, {})

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def __enter__(self) -> _StubClient:
        return self

    def __exit__(self, *args) -> None:
        return None

    def post(self, path: str, *, headers: dict, json: dict) -> _StubResponse:
        type(self).calls.append({"path": path, "headers": headers, "json": json})
        if isinstance(type(self).response, Exception):
            raise type(self).response
        return type(self).response


@pytest.fixture()
def stub_http(monkeypatch: pytest.MonkeyPatch):
    _StubClient.calls = []
    monkeypatch.setattr("app.providers.groq.client.httpx.Client", _StubClient)
    monkeypatch.setattr("app.providers.groq.client.time.sleep", lambda _: None)
    return _StubClient


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "gnani_api_key": "test-gnani-key",
        "groq_api_key": "test-groq-key",
        "groq_max_retries": 0,
    }
    values.update(overrides)
    return Settings(**values)


def _call(settings: Settings) -> None:
    GroqClient(settings).chat_json(
        system_prompt="system",
        user_payload={"text": "hello"},
        schema_model=_Schema,
        schema_name="test_schema",
        prompt_version="test_v1",
    )


def test_auth_failure_propagates_without_retry_or_fallback(stub_http):
    stub_http.response = _StubResponse(401, {"error": {"message": "invalid key"}})

    with pytest.raises(ProviderAuthError):
        _call(_settings())

    assert len(stub_http.calls) == 1


def test_schema_failure_propagates_without_best_effort_retry(stub_http):
    stub_http.response = _StubResponse(
        200,
        {
            "choices": [
                {
                    "message": {"content": "this is not valid json"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {},
        },
    )

    with pytest.raises(ProviderSchemaError):
        _call(_settings(groq_strict_schema=True))

    assert len(stub_http.calls) == 1
    assert stub_http.calls[0]["json"]["response_format"]["type"] == "json_schema"


def test_rate_limit_is_retried_then_raised(stub_http):
    stub_http.response = _StubResponse(429, {"error": {"message": "slow down"}})

    with pytest.raises(ProviderRateLimitError):
        _call(_settings(groq_max_retries=1))

    assert len(stub_http.calls) == 2


def test_client_error_is_reported_without_model_or_schema_fallback(stub_http):
    stub_http.response = _StubResponse(400, {"error": {"message": "bad request"}})

    with pytest.raises(ProviderResponseError, match="HTTP 400"):
        _call(_settings(groq_strict_schema=True))

    assert len(stub_http.calls) == 1


def test_timeout_is_retried_then_normalized(stub_http):
    stub_http.response = httpx.TimeoutException("timed out")

    with pytest.raises(ProviderTimeoutError):
        _call(_settings(groq_max_retries=1))

    assert len(stub_http.calls) == 2
