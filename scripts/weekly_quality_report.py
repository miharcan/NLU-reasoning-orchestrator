from __future__ import annotations

import json
from datetime import datetime, timezone

from eval.evaluate import compute_eval_metrics


def main() -> None:
    metrics = compute_eval_metrics().as_dict()
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "service": "nlu-reasoning-orchestrator",
        "summary": {
            "intent_accuracy": round(metrics["intent_accuracy"], 4),
            "json_validity": round(metrics["json_validity"], 4),
            "multi_intent_detection_rate": round(metrics["multi_intent_detection_rate"], 4),
            "fallback_rate": round(metrics["fallback_rate"], 4),
            "avg_latency_ms": round(metrics["avg_latency_ms"], 2),
        },
        "notes": [
            "Use this report in weekly delivery review.",
            "If any KPI regresses, investigate test cases and recent model/prompt/policy changes.",
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
