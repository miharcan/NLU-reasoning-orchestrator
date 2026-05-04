from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.orchestrator import NLUReasoningOrchestrator


@dataclass
class ConversationMetrics:
    total_conversations: int
    passed_conversations: int
    total_turns: int
    passed_turns: int
    conversation_pass_rate: float
    turn_pass_rate: float
    failure_taxonomy: Dict[str, int]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total_conversations": self.total_conversations,
            "passed_conversations": self.passed_conversations,
            "total_turns": self.total_turns,
            "passed_turns": self.passed_turns,
            "conversation_pass_rate": self.conversation_pass_rate,
            "turn_pass_rate": self.turn_pass_rate,
            "failure_taxonomy": self.failure_taxonomy,
        }


def _inc(counter: Dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _check_turn(
    expected: Dict[str, Any],
    response,
    state,
) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if "primary_intent" in expected and response.decision.primary_intent != expected["primary_intent"]:
        errors.append("wrong_intent")

    if "next_action" in expected and response.decision.next_action != expected["next_action"]:
        if expected["next_action"] == "escalate" or response.decision.next_action == "escalate":
            errors.append("wrong_escalation")
        else:
            errors.append("wrong_action")

    if "authenticated" in expected and state.authenticated != expected["authenticated"]:
        errors.append("auth_miss")

    if "missing_slots_contains" in expected:
        required = set(expected["missing_slots_contains"])
        actual = set(state.missing_slots)
        if not required.issubset(actual):
            errors.append("slot_miss")

    if "missing_slots_equals" in expected:
        if set(state.missing_slots) != set(expected["missing_slots_equals"]):
            errors.append("slot_miss")

    if "secondary_intents_contains" in expected:
        required_secondary = set(expected["secondary_intents_contains"])
        actual_secondary = set(response.decision.secondary_intents)
        if not required_secondary.issubset(actual_secondary):
            errors.append("wrong_intent")

    return len(errors) == 0, errors


def compute_state_transition_metrics(
    test_file: Path | None = None,
) -> ConversationMetrics:
    os.environ.setdefault("ADJUDICATOR_MODE", "mock")
    test_file = test_file or (Path(__file__).parent / "conversations.json")
    conversations = json.loads(test_file.read_text())

    orchestrator = NLUReasoningOrchestrator()

    total_conversations = len(conversations)
    passed_conversations = 0
    total_turns = 0
    passed_turns = 0
    failure_taxonomy: Dict[str, int] = {}

    for convo in conversations:
        convo_passed = True
        for turn in convo["turns"]:
            total_turns += 1
            response = orchestrator.analyze(
                session_id=convo["session_id"],
                user_id=convo["user_id"],
                utterance=turn["utterance"],
            )
            state = orchestrator.state_store.get_or_create(
                session_id=convo["session_id"],
                user_id=convo["user_id"],
            )
            turn_pass, errors = _check_turn(turn.get("expected", {}), response, state)
            if turn_pass:
                passed_turns += 1
            else:
                convo_passed = False
                for err in errors:
                    _inc(failure_taxonomy, err)

        if convo_passed:
            passed_conversations += 1

    convo_pass_rate = (passed_conversations / total_conversations) if total_conversations else 1.0
    turn_pass_rate = (passed_turns / total_turns) if total_turns else 1.0

    for key in ["auth_miss", "slot_miss", "wrong_action", "wrong_escalation", "wrong_intent"]:
        failure_taxonomy.setdefault(key, 0)

    return ConversationMetrics(
        total_conversations=total_conversations,
        passed_conversations=passed_conversations,
        total_turns=total_turns,
        passed_turns=passed_turns,
        conversation_pass_rate=convo_pass_rate,
        turn_pass_rate=turn_pass_rate,
        failure_taxonomy=failure_taxonomy,
    )


def run_state_transition_eval() -> None:
    metrics = compute_state_transition_metrics()
    print("=== Multi-turn State Transition Evaluation ===")
    print(f"Conversations: {metrics.passed_conversations}/{metrics.total_conversations} passed")
    print(f"Conversation pass rate: {metrics.conversation_pass_rate:.2%}")
    print(f"Turn pass rate: {metrics.turn_pass_rate:.2%}")
    print("Failure taxonomy:")
    for name, count in metrics.failure_taxonomy.items():
        print(f"- {name}: {count}")


if __name__ == "__main__":
    run_state_transition_eval()
