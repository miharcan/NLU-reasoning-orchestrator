from app.policy import PolicyEngine
from app.schemas import NLUDecision


def test_policy_denies_unauthenticated_tool_call() -> None:
    policy = PolicyEngine()
    decision = NLUDecision(
        primary_intent="update_payment_method",
        secondary_intents=[],
        entities={"card_last4": "1234"},
        missing_slots=[],
        risk_level="medium",
        next_action="call_tool",
        reasoning="Tool call should be blocked until user is authenticated.",
    )

    result = policy.validate(decision=decision, authenticated=False)

    assert result.allowed is False
    assert "authentication" in result.reason.lower()


def test_policy_blocks_high_risk_auto_answer() -> None:
    policy = PolicyEngine()
    decision = NLUDecision(
        primary_intent="lost_card",
        secondary_intents=[],
        entities={},
        missing_slots=[],
        risk_level="high",
        next_action="answer",
        reasoning="This is intentionally unsafe for validation.",
    )

    result = policy.validate(decision=decision, authenticated=True)

    assert result.allowed is False
    assert "high-risk" in result.reason.lower()
