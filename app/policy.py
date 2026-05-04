from __future__ import annotations

from app.schemas import NLUDecision, PolicyResult


class PolicyEngine:
    def validate(self, decision: NLUDecision, authenticated: bool) -> PolicyResult:
        if decision.next_action == "call_tool" and not authenticated:
            return PolicyResult(
                allowed=False,
                reason="Tool calls require authentication first.",
            )
        if decision.risk_level == "high" and decision.next_action == "answer":
            return PolicyResult(
                allowed=False,
                reason="High-risk intents cannot be auto-answered.",
            )
        return PolicyResult(allowed=True, reason="Action is policy-compliant.")
