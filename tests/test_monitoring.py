from app.monitoring import DecisionMonitor
from app.schemas import IntentScore, NLUDecision, OrchestratorResponse, PolicyResult


def _response(latency_ms: float, next_action: str = "answer") -> OrchestratorResponse:
    return OrchestratorResponse(
        session_id="s",
        nlu_candidates=[IntentScore(intent="check_balance", confidence=0.8)],
        decision=NLUDecision(
            primary_intent="check_balance",
            secondary_intents=[],
            entities={},
            missing_slots=[],
            risk_level="low",
            next_action=next_action,
            reasoning="Synthetic response for monitoring test.",
        ),
        policy=PolicyResult(allowed=True, reason="ok"),
        tool_results=None,
        latency_ms=latency_ms,
    )


def test_snapshot_includes_percentiles() -> None:
    monitor = DecisionMonitor()
    for latency in [100.0, 200.0, 300.0, 400.0, 500.0]:
        monitor.record(_response(latency))

    snapshot = monitor.snapshot()

    assert snapshot["p50_latency_ms"] > 0
    assert snapshot["p95_latency_ms"] >= snapshot["p50_latency_ms"]


def test_slo_status_flags_breach() -> None:
    monitor = DecisionMonitor()
    monitor.record(_response(2000.0, next_action="ask_clarification"))

    status = monitor.slo_status(
        {
            "p95_latency_ms": 500.0,
            "fallback_rate": 0.1,
            "policy_denial_rate": 0.1,
            "json_validity_rate": 0.99,
        }
    )

    assert status["all_slos_met"] is False
    assert status["checks"]["p95_latency_ms"] is False
    assert status["checks"]["fallback_rate"] is False
