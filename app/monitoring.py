from __future__ import annotations

from collections import Counter, deque
from statistics import mean, median
from threading import Lock
from typing import Any, Deque, Dict

from app.schemas import OrchestratorResponse


class DecisionMonitor:
    """Thread-safe in-memory operational telemetry for the orchestrator service."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._total_requests = 0
        self._policy_denials = 0
        self._json_valid_count = 0
        self._multi_intent_count = 0
        self._fallback_count = 0
        self._intent_counter: Counter[str] = Counter()
        self._action_counter: Counter[str] = Counter()
        self._risk_counter: Counter[str] = Counter()
        self._latencies_ms: Deque[float] = deque(maxlen=1000)

    def record(self, response: OrchestratorResponse) -> None:
        with self._lock:
            self._total_requests += 1
            decision = response.decision

            self._intent_counter[decision.primary_intent] += 1
            self._action_counter[decision.next_action] += 1
            self._risk_counter[decision.risk_level] += 1
            self._latencies_ms.append(response.latency_ms)

            if not response.policy.allowed:
                self._policy_denials += 1

            if len(decision.secondary_intents) > 0:
                self._multi_intent_count += 1

            if decision.next_action == "ask_clarification":
                self._fallback_count += 1

            # If response exists as pydantic object, it's schema-valid.
            if response.model_dump():
                self._json_valid_count += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            total = self._total_requests
            avg_latency = mean(self._latencies_ms) if self._latencies_ms else 0.0
            p50_latency = median(self._latencies_ms) if self._latencies_ms else 0.0
            p95_latency = self._percentile(self._latencies_ms, 95.0)

            def ratio(count: int) -> float:
                return round((count / total), 4) if total else 0.0

            return {
                "total_requests": total,
                "policy_denials": self._policy_denials,
                "policy_denial_rate": ratio(self._policy_denials),
                "multi_intent_rate": ratio(self._multi_intent_count),
                "fallback_rate": ratio(self._fallback_count),
                "json_validity_rate": ratio(self._json_valid_count),
                "avg_latency_ms": round(avg_latency, 3),
                "p50_latency_ms": round(p50_latency, 3),
                "p95_latency_ms": round(p95_latency, 3),
                "intent_distribution": dict(self._intent_counter),
                "action_distribution": dict(self._action_counter),
                "risk_distribution": dict(self._risk_counter),
            }

    def slo_status(self, targets: Dict[str, float]) -> Dict[str, Any]:
        snapshot = self.snapshot()
        checks = {
            "p95_latency_ms": snapshot["p95_latency_ms"] <= targets["p95_latency_ms"],
            "fallback_rate": snapshot["fallback_rate"] <= targets["fallback_rate"],
            "policy_denial_rate": snapshot["policy_denial_rate"] <= targets["policy_denial_rate"],
            "json_validity_rate": snapshot["json_validity_rate"] >= targets["json_validity_rate"],
        }
        return {
            "targets": targets,
            "snapshot": {
                "total_requests": snapshot["total_requests"],
                "p95_latency_ms": snapshot["p95_latency_ms"],
                "fallback_rate": snapshot["fallback_rate"],
                "policy_denial_rate": snapshot["policy_denial_rate"],
                "json_validity_rate": snapshot["json_validity_rate"],
            },
            "checks": checks,
            "all_slos_met": all(checks.values()),
        }

    def _percentile(self, values: Deque[float], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        raw_index = int(round((percentile / 100.0) * (len(sorted_values) - 1)))
        index = max(0, min(len(sorted_values) - 1, raw_index))
        return float(sorted_values[index])
