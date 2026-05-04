from app.monitoring import DecisionMonitor
from app.orchestrator import NLUReasoningOrchestrator


class BrokenAdjudicator:
    def decide(self, utterance, candidates, entities, authenticated):
        raise TimeoutError("simulated upstream timeout")


def test_multi_intent_and_auth_next_action() -> None:
    monitor = DecisionMonitor()
    orchestrator = NLUReasoningOrchestrator(monitor=monitor)

    response = orchestrator.analyze(
        session_id="s-1",
        user_id="u-1",
        utterance="I was charged twice last month and I need to update the card on file.",
    )

    assert response.decision.primary_intent == "billing_dispute"
    assert "update_payment_method" in response.decision.secondary_intents
    assert response.decision.next_action == "authenticate_user"
    assert response.decision.risk_level == "medium"


def test_authenticated_tool_execution_path() -> None:
    monitor = DecisionMonitor()
    orchestrator = NLUReasoningOrchestrator(monitor=monitor)

    # First turn simulates successful authentication marker.
    orchestrator.analyze(
        session_id="s-2",
        user_id="u-2",
        utterance="authenticate me, otp code is 123456",
    )

    response = orchestrator.analyze(
        session_id="s-2",
        user_id="u-2",
        utterance="Please update the card on file ending in 9812",
    )

    assert response.decision.primary_intent == "update_payment_method"
    assert response.decision.next_action == "call_tool"
    assert response.tool_results is not None
    assert response.tool_results.get("status") == "updated"
    assert response.tool_results.get("card_last4") == "9812"


def test_monitoring_snapshot_updates() -> None:
    monitor = DecisionMonitor()
    orchestrator = NLUReasoningOrchestrator(monitor=monitor)

    orchestrator.analyze(
        session_id="s-3",
        user_id="u-3",
        utterance="I lost my debit card",
    )

    snapshot = monitor.snapshot()

    assert snapshot["total_requests"] == 1
    assert "lost_card" in snapshot["intent_distribution"]


def test_adjudicator_failure_uses_fallback() -> None:
    monitor = DecisionMonitor()
    orchestrator = NLUReasoningOrchestrator(monitor=monitor, adjudicator=BrokenAdjudicator())

    response = orchestrator.analyze(
        session_id="s-4",
        user_id="u-4",
        utterance="I was charged twice last month",
    )

    assert response.decision.primary_intent == "billing_dispute"
    assert "Fallback adjudicator used" in response.decision.reasoning
