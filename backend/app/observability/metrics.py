from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ProviderMetric:
    calls: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    last_error_code: str | None = None

    @property
    def average_latency_ms(self) -> float:
        if self.calls == 0:
            return 0.0
        return round(self.total_latency_ms / self.calls, 2)


@dataclass
class MetricsRegistry:
    _providers: dict[str, ProviderMetric] = field(
        default_factory=lambda: defaultdict(ProviderMetric)
    )
    _lock: Lock = field(default_factory=Lock)
    _end_to_end: list[float] = field(default_factory=list)

    def record_provider_call(
        self,
        provider: str,
        operation: str,
        latency_ms: float,
        *,
        success: bool,
        error_code: str | None = None,
    ) -> None:
        key = f"{provider}.{operation}"
        with self._lock:
            metric = self._providers[key]
            metric.calls += 1
            metric.total_latency_ms += max(latency_ms, 0.0)
            if not success:
                metric.failures += 1
                metric.last_error_code = error_code

    def record_end_to_end(self, latency_ms: float) -> None:
        with self._lock:
            self._end_to_end.append(max(latency_ms, 0.0))
            if len(self._end_to_end) > 500:
                self._end_to_end = self._end_to_end[-500:]

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            providers = {
                key: {
                    "calls": metric.calls,
                    "failures": metric.failures,
                    "average_latency_ms": metric.average_latency_ms,
                    "last_error_code": metric.last_error_code,
                }
                for key, metric in self._providers.items()
            }
            e2e = list(self._end_to_end)
        return {
            "providers": providers,
            "end_to_end": {
                "samples": len(e2e),
                "average_latency_ms": round(sum(e2e) / len(e2e), 2) if e2e else 0.0,
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._providers.clear()
            self._end_to_end.clear()


metrics = MetricsRegistry()
