from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict

from app.orchestrator import NLUReasoningOrchestrator


def build_per_intent_report(test_file: Path | None = None) -> Dict[str, object]:
    orchestrator = NLUReasoningOrchestrator()
    test_file = test_file or (Path(__file__).parent / "test_cases.json")
    test_cases = json.loads(test_file.read_text())

    counts = defaultdict(int)
    correct = defaultdict(int)
    predicted = defaultdict(int)
    confusion = defaultdict(lambda: defaultdict(int))

    for i, case in enumerate(test_cases, start=1):
        expected = case["expected_intent"]
        response = orchestrator.analyze(
            session_id=f"per-intent-{i}",
            user_id="eval-user",
            utterance=case["utterance"],
        )
        actual = response.decision.primary_intent

        counts[expected] += 1
        predicted[actual] += 1
        confusion[expected][actual] += 1
        if actual == expected:
            correct[expected] += 1

    intents = sorted(set(counts.keys()) | set(predicted.keys()))
    per_intent = {}
    for intent in intents:
        support = counts[intent]
        recall = (correct[intent] / support) if support else 0.0
        per_intent[intent] = {
            "support": support,
            "correct": correct[intent],
            "recall": round(recall, 4),
            "predicted_count": predicted[intent],
        }

    confusion_matrix = {
        expected: {pred: confusion[expected][pred] for pred in intents if confusion[expected][pred] > 0}
        for expected in intents
    }

    return {
        "total_cases": len(test_cases),
        "intents": per_intent,
        "confusion_matrix": confusion_matrix,
    }


def main() -> None:
    report = build_per_intent_report()
    print("=== Per-Intent Evaluation Report ===")
    for intent, metrics in sorted(report["intents"].items()):
        print(
            f"- {intent}: support={metrics['support']} correct={metrics['correct']} "
            f"recall={metrics['recall']:.2%} predicted={metrics['predicted_count']}"
        )
    print("\\nConfusion matrix:")
    print(json.dumps(report["confusion_matrix"], indent=2))


if __name__ == "__main__":
    main()
