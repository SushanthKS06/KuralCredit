from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import REPO_ROOT
from app.core.exceptions import ConfigurationError

PROFILES_PATH = REPO_ROOT / "backend" / "app" / "config" / "document_profiles.json"


class ColumnAliases(BaseModel):
    date: list[str] = Field(default_factory=list)
    description: list[str] = Field(default_factory=list)
    credit: list[str] = Field(default_factory=list)
    debit: list[str] = Field(default_factory=list)
    amount: list[str] = Field(default_factory=list)
    period: list[str] = Field(default_factory=list)
    turnover: list[str] = Field(default_factory=list)
    invoice: list[str] = Field(default_factory=list)
    payment_mode: list[str] = Field(default_factory=list)


class DocumentProfile(BaseModel):
    label: str
    document_type: str
    field_key: str
    measure_type: str
    source_type: str
    columns: ColumnAliases
    date_formats: list[str] = Field(default_factory=list)
    aggregation: str
    notes: str = ""


class DocumentProfileCatalog(BaseModel):
    version: str
    profiles: dict[str, DocumentProfile]


@lru_cache
def get_document_profiles() -> DocumentProfileCatalog:
    path = Path(PROFILES_PATH)
    if not path.exists():
        raise ConfigurationError(f"Document profile catalogue missing at {path}")
    with path.open("r", encoding="utf-8") as handle:
        return DocumentProfileCatalog.model_validate(json.load(handle))


def get_profile(document_type: str) -> DocumentProfile:
    catalog = get_document_profiles()
    profile = catalog.profiles.get(document_type)
    if profile is None:
        raise ConfigurationError(f"Unknown document profile: {document_type}")
    return profile


def detect_document_type(headers: list[str]) -> str | None:
    normalized = {header.strip().lower() for header in headers}
    best: tuple[int, str] | None = None
    for name, profile in get_document_profiles().profiles.items():
        aliases = {
            alias.lower() for values in profile.columns.model_dump().values() for alias in values
        }
        score = len(normalized & aliases)
        if score and (best is None or score > best[0]):
            best = (score, name)
    return best[1] if best else None
