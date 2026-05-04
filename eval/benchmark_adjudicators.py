from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterator, List

from app.orchestrator import NLUReasoningOrchestrator
from eval.evaluate import EvalMetrics, compute_eval_metrics


@dataclass
class BenchmarkRow:
    name: str
    metrics: EvalMetrics
    wall_seconds: float

    def as_dict(self) -> Dict[str, float | int | str]:
        return {
            "name": self.name,
            "intent_accuracy": round(self.metrics.intent_accuracy, 4),
            "json_validity": round(self.metrics.json_validity, 4),
            "multi_intent_detection_rate": round(self.metrics.multi_intent_detection_rate, 4),
            "fallback_rate": round(self.metrics.fallback_rate, 4),
            "avg_latency_ms": round(self.metrics.avg_latency_ms, 2),
            "wall_seconds": round(self.wall_seconds, 2),
        }


@contextmanager
def temporary_env(updates: Dict[str, str]) -> Iterator[None]:
    original = {k: os.environ.get(k) for k in updates}
    try:
        for key, value in updates.items():
            os.environ[key] = value
        yield
    finally:
        for key, previous in original.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def run_profile(name: str, env: Dict[str, str]) -> BenchmarkRow:
    with temporary_env(env):
        start = time.perf_counter()
        orchestrator = NLUReasoningOrchestrator()
        metrics = compute_eval_metrics(orchestrator=orchestrator)
        wall = time.perf_counter() - start
    return BenchmarkRow(name=name, metrics=metrics, wall_seconds=wall)


def print_table(rows: List[BenchmarkRow]) -> None:
    headers = [
        "profile",
        "intent_acc",
        "json_valid",
        "multi_intent",
        "fallback",
        "avg_latency_ms",
        "wall_s",
    ]
    line = " | ".join(headers)
    print(line)
    print("-" * len(line))
    for row in rows:
        m = row.metrics
        print(
            " | ".join(
                [
                    row.name,
                    f"{m.intent_accuracy:.2%}",
                    f"{m.json_validity:.2%}",
                    f"{m.multi_intent_detection_rate:.2%}",
                    f"{m.fallback_rate:.2%}",
                    f"{m.avg_latency_ms:.2f}",
                    f"{row.wall_seconds:.2f}",
                ]
            )
        )


def main() -> None:
    ollama_url = os.getenv(
        "BENCH_HTTP_ADJUDICATOR_URL",
        "https://ollama-gateway-demo-nyp4v3bf6a-uc.a.run.app/adjudicate",
    )
    http_timeout = os.getenv("BENCH_HTTP_ADJUDICATOR_TIMEOUT_SECONDS", "12")
    http_cooldown = os.getenv("BENCH_HTTP_ADJUDICATOR_COOLDOWN_SECONDS", "180")

    profiles = [
        (
            "mock",
            {
                "ADJUDICATOR_MODE": "mock",
            },
        ),
        (
            "http_ollama",
            {
                "ADJUDICATOR_MODE": "http",
                "ADJUDICATOR_HTTP_URL": ollama_url,
                "ADJUDICATOR_HTTP_TIMEOUT_SECONDS": http_timeout,
                "ADJUDICATOR_HTTP_COOLDOWN_SECONDS": http_cooldown,
            },
        ),
    ]

    rows: List[BenchmarkRow] = []
    for name, env in profiles:
        print(f"Running profile: {name}")
        rows.append(run_profile(name=name, env=env))

    print("\n=== Adjudicator Benchmark (Step 2) ===")
    print_table(rows)


if __name__ == "__main__":
    main()
