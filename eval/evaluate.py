from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from app.orchestrator import NLUReasoningOrchestrator


@dataclass
class EvalMetrics:
    total_cases: int
    intent_accuracy: float
    fallback_rate: float
    multi_intent_detection_rate: float
    json_validity: float
    avg_latency_ms: float

    def as_dict(self) -> Dict[str, float | int]:
        return {
            "total_cases": self.total_cases,
            "intent_accuracy": self.intent_accuracy,
            "fallback_rate": self.fallback_rate,
            "multi_intent_detection_rate": self.multi_intent_detection_rate,
            "json_validity": self.json_validity,
            "avg_latency_ms": self.avg_latency_ms,
        }


def compute_eval_metrics(
    orchestrator: Optional[NLUReasoningOrchestrator] = None,
    test_file: Optional[Path] = None,
) -> EvalMetrics:
    orchestrator = orchestrator or NLUReasoningOrchestrator()
    test_file = test_file or (Path(__file__).parent / "test_cases.json")
    test_cases = json.loads(test_file.read_text())

    correct = 0
    fallback = 0
    multi_tp = 0
    multi_total = 0
    valid_json = 0
    latencies = []

    for i, case in enumerate(test_cases, start=1):
        response = orchestrator.analyze(
            session_id=f"eval-session-{i}",
            user_id="eval-user",
            utterance=case["utterance"],
        )
        decision = response.decision
        latencies.append(response.latency_ms)

        if decision.primary_intent == case["expected_intent"]:
            correct += 1

        if decision.next_action == "ask_clarification":
            fallback += 1

        expected_multi = case["expected_multi_intent"]
        predicted_multi = len(decision.secondary_intents) > 0
        if expected_multi:
            multi_total += 1
            if predicted_multi:
                multi_tp += 1

        # If pydantic constructed response, schema is valid.
        if response.model_dump():
            valid_json += 1

    total = len(test_cases)
    accuracy = correct / total
    fallback_rate = fallback / total
    multi_intent_rate = (multi_tp / multi_total) if multi_total else 1.0
    json_validity = valid_json / total
    avg_latency = statistics.mean(latencies)

    return EvalMetrics(
        total_cases=total,
        intent_accuracy=accuracy,
        fallback_rate=fallback_rate,
        multi_intent_detection_rate=multi_intent_rate,
        json_validity=json_validity,
        avg_latency_ms=avg_latency,
    )


def run_eval() -> None:
    metrics = compute_eval_metrics()
    print("=== NLU Reasoning Orchestrator Evaluation ===")
    print(f"Total cases: {metrics.total_cases}")
    print(f"Intent accuracy: {metrics.intent_accuracy:.2%}")
    print(f"Fallback rate: {metrics.fallback_rate:.2%}")
    print(f"Multi-intent detection rate: {metrics.multi_intent_detection_rate:.2%}")
    print(f"JSON validity: {metrics.json_validity:.2%}")
    print(f"Average latency (ms): {metrics.avg_latency_ms:.2f}")


if __name__ == "__main__":
    run_eval()
