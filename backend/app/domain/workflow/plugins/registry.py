from __future__ import annotations

from typing import Any

from app.domain.workflow.plugins.base import RulePlugin
from app.domain.workflow.plugins.financial_reconciliation import FinancialReconciliationPlugin
from app.domain.workflow.plugins.support_triage import SupportTriagePlugin


class RulePluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, RulePlugin] = {}
        # Register standard built-in plugins
        self.register(FinancialReconciliationPlugin())
        self.register(SupportTriagePlugin())

    def register(self, plugin: RulePlugin) -> None:
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> RulePlugin | None:
        return self._plugins.get(name)

    def evaluate_all(
        self,
        rule_names: list[str],
        application: Any,
        workflow: Any,
        facts: list[Any],
        documents: list[Any],
    ) -> list[Any]:
        results = []
        for name in rule_names:
            plugin = self.get(name)
            if plugin:
                results.append(plugin.evaluate(application, workflow, facts, documents))
        return results


_default_rule_registry = RulePluginRegistry()


def get_rule_registry() -> RulePluginRegistry:
    return _default_rule_registry
