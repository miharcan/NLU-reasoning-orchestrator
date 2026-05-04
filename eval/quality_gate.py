from __future__ import annotations

import os

from eval.evaluate import compute_eval_metrics

THRESHOLDS = {
    "intent_accuracy": float(os.getenv("EVAL_MIN_INTENT_ACCURACY", "0.90")),
    "json_validity": float(os.getenv("EVAL_MIN_JSON_VALIDITY", "0.99")),
    "multi_intent_detection_rate": float(os.getenv("EVAL_MIN_MULTI_INTENT_DETECTION_RATE", "0.70")),
    "fallback_rate": float(os.getenv("EVAL_MAX_FALLBACK_RATE", "0.40")),
    "avg_latency_ms": float(os.getenv("EVAL_MAX_AVG_LATENCY_MS", "1500")),
}


def main() -> int:
    metrics = compute_eval_metrics().as_dict()

    print("=== Quality Gate ===")
    for key, value in metrics.items():
        print(f"{key}: {value}")

    failures: list[str] = []
    if metrics["intent_accuracy"] < THRESHOLDS["intent_accuracy"]:
        failures.append(
            f"intent_accuracy {metrics['intent_accuracy']:.4f} < {THRESHOLDS['intent_accuracy']:.4f}"
        )
    if metrics["json_validity"] < THRESHOLDS["json_validity"]:
        failures.append(
            f"json_validity {metrics['json_validity']:.4f} < {THRESHOLDS['json_validity']:.4f}"
        )
    if metrics["multi_intent_detection_rate"] < THRESHOLDS["multi_intent_detection_rate"]:
        failures.append(
            "multi_intent_detection_rate "
            f"{metrics['multi_intent_detection_rate']:.4f} < {THRESHOLDS['multi_intent_detection_rate']:.4f}"
        )
    if metrics["fallback_rate"] > THRESHOLDS["fallback_rate"]:
        failures.append(
            f"fallback_rate {metrics['fallback_rate']:.4f} > {THRESHOLDS['fallback_rate']:.4f}"
        )
    if metrics["avg_latency_ms"] > THRESHOLDS["avg_latency_ms"]:
        failures.append(
            f"avg_latency_ms {metrics['avg_latency_ms']:.2f} > {THRESHOLDS['avg_latency_ms']:.2f}"
        )

    if failures:
        print("\\nQUALITY GATE FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\\nQUALITY GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
