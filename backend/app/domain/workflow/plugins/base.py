from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class RuleClarificationItem:
    field_key: str
    question_text: str
    reason: str
    priority: int = 100
    expected_answer_type: str = "text"


@dataclass
class RuleEvaluationResult:
    requires_clarification: bool = False
    clarifications: list[RuleClarificationItem] = field(default_factory=list)
    comparisons: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    flags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class RulePlugin(Protocol):
    @property
    def name(self) -> str: ...

    def evaluate(
        self,
        application: Any,
        workflow: Any,
        facts: list[Any],
        documents: list[Any],
    ) -> RuleEvaluationResult: ...
