from __future__ import annotations

from typing import Any, cast

import pytest

from app.core.config import Settings


def test_gnani_api_key_is_required():
    with pytest.raises(ValueError, match="GNANI_API_KEY"):
        Settings(_env_file=None, gnani_api_key=None)


def test_groq_api_key_is_required():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        Settings(_env_file=None, groq_api_key=None)


def test_mock_mode_is_explicit_and_allows_missing_keys():
    settings = Settings(
        _env_file=None,
        provider_mode="mock",
        gnani_api_key=None,
        groq_api_key=None,
    )
    assert settings.is_mock_mode is True


def test_mock_mode_is_rejected_in_production():
    with pytest.raises(ValueError, match="mock is not allowed in production"):
        Settings(
            _env_file=None,
            app_env="production",
            provider_mode="mock",
            gnani_api_key=None,
            groq_api_key=None,
        )


def test_unknown_provider_mode_is_rejected():
    with pytest.raises(ValueError, match="provider_mode"):
        Settings(_env_file=None, provider_mode=cast(Any, "auto"))
