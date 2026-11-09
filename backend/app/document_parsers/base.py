from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TableData:
    name: str
    headers: list[str]
    rows: list[dict[str, Any]]
    row_numbers: list[int]
    sheet: str | None = None


@dataclass
class ParsedDocument:
    text: str
    readable: bool
    page_count: int | None = None
    locators: list[dict[str, str]] = field(default_factory=list)
    tables: list[TableData] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class DocumentParser(ABC):
    name: str
    extensions: frozenset[str]

    @abstractmethod
    def parse(self, content: bytes) -> ParsedDocument:
        raise NotImplementedError
