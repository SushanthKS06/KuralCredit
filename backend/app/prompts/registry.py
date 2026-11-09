from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

from app.core.exceptions import ConfigurationError

PROMPT_DIR = Path(__file__).resolve().parent
VERSION_PATTERN = re.compile(r"^(?P<name>.+)_(?P<version>v\d+)$")


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    text: str
    sha256: str

    def render(self, **variables: object) -> str:
        try:
            return Template(self.text).substitute(**variables)
        except KeyError as exc:
            raise ConfigurationError(
                f"Prompt {self.name} is missing required variable {exc.args[0]}"
            ) from exc


class PromptRegistry:
    def __init__(self, directory: Path = PROMPT_DIR) -> None:
        self.directory = directory
        self._templates: dict[str, PromptTemplate] = {}
        self._load()

    def _load(self) -> None:
        for path in sorted(self.directory.glob("*.txt")):
            stem = path.stem
            match = VERSION_PATTERN.match(stem)
            if not match:
                continue
            text = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            template = PromptTemplate(
                name=match.group("name"),
                version=match.group("version"),
                text=text,
                sha256=digest,
            )
            self._templates[template.name] = template

    def get(self, name: str) -> PromptTemplate:
        template = self._templates.get(name)
        if template is None:
            raise ConfigurationError(f"Prompt template '{name}' is not registered")
        return template

    def list(self) -> list[dict[str, str]]:
        return [
            {"name": template.name, "version": template.version, "sha256": template.sha256}
            for template in self._templates.values()
        ]
