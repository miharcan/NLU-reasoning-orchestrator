from __future__ import annotations

import os

from eval.state_transition_eval import compute_state_transition_metrics

MIN_CONVERSATION_PASS_RATE = float(os.getenv("MIN_CONVERSATION_PASS_RATE", "0.90"))
MIN_TURN_PASS_RATE = float(os.getenv("MIN_TURN_PASS_RATE", "0.95"))


def main() -> int:
    metrics = compute_state_transition_metrics().as_dict()

    print("=== Conversation Quality Gate ===")
    for key, value in metrics.items():
        print(f"{key}: {value}")

    failures: list[str] = []
    if metrics["conversation_pass_rate"] < MIN_CONVERSATION_PASS_RATE:
        failures.append(
            "conversation_pass_rate "
            f"{metrics['conversation_pass_rate']:.4f} < {MIN_CONVERSATION_PASS_RATE:.4f}"
        )
    if metrics["turn_pass_rate"] < MIN_TURN_PASS_RATE:
        failures.append(f"turn_pass_rate {metrics['turn_pass_rate']:.4f} < {MIN_TURN_PASS_RATE:.4f}")

    if failures:
        print("\nCONVERSATION QUALITY GATE FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nCONVERSATION QUALITY GATE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
