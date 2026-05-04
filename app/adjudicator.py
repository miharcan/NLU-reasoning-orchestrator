from __future__ import annotations

from typing import Dict, List

from app.schemas import IntentScore, NLUDecision


class MockLLMAdjudicator:
    """
    Rule-based stand-in for an LLM adjudicator.
    Keeps architecture realistic while staying local/offline.
    """

    def decide(
        self,
        utterance: str,
        candidates: List[IntentScore],
        entities: Dict[str, str],
        authenticated: bool,
    ) -> NLUDecision:
        text = utterance.lower()
        sorted_candidates = sorted(candidates, key=lambda c: c.confidence, reverse=True)
        top = sorted_candidates[0]
        second = sorted_candidates[1] if len(sorted_candidates) > 1 else None

        is_ambiguous = second is not None and abs(top.confidence - second.confidence) < 0.12
        has_connector = any(token in text for token in [" and ", " also ", " but ", " as well as "])
        has_multi_intent = second is not None and (
            second.confidence >= 0.48 or (has_connector and second.confidence >= 0.4)
        )

        primary_intent = top.intent
        secondary_intents = [second.intent] if has_multi_intent else []

        has_dispute_signal = any(
            word in text for word in ["wrong", "charged", "dispute", "incorrect", "twice", "billed"]
        )
        if has_multi_intent and {top.intent, second.intent} == {"make_payment", "billing_dispute"}:
            primary_intent = "billing_dispute"
            secondary_intents = ["make_payment"]
        elif has_dispute_signal and primary_intent == "make_payment":
            primary_intent = "billing_dispute"
            if second and second.intent != "billing_dispute":
                secondary_intents = [second.intent]

        missing_slots = self._required_missing_slots(primary_intent, entities)
        risk_level = self._risk_level(primary_intent, secondary_intents)

        if primary_intent == "speak_to_agent":
            next_action = "escalate"
        elif not authenticated and self._needs_auth(primary_intent, secondary_intents):
            next_action = "authenticate_user"
        elif is_ambiguous:
            next_action = "ask_clarification"
        elif missing_slots:
            next_action = "ask_clarification"
        elif primary_intent in {
            "billing_dispute",
            "make_payment",
            "update_payment_method",
            "lost_card",
            "change_address",
        }:
            next_action = "call_tool"
        else:
            next_action = "answer"

        reasoning = self._reasoning(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            is_ambiguous=is_ambiguous,
            missing_slots=missing_slots,
            next_action=next_action,
        )

        return NLUDecision(
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            entities=entities,
            missing_slots=missing_slots,
            risk_level=risk_level,
            next_action=next_action,
            reasoning=reasoning,
        )

    def _required_missing_slots(self, intent: str, entities: Dict[str, str]) -> List[str]:
        required_by_intent = {
            "billing_dispute": ["transaction_amount", "transaction_date"],
            "make_payment": ["payment_amount"],
            "update_payment_method": ["card_last4"],
            "change_address": ["new_address"],
        }
        required = required_by_intent.get(intent, [])
        return [slot for slot in required if slot not in entities]

    def _risk_level(self, primary_intent: str, secondary_intents: List[str]) -> str:
        high = {"lost_card"}
        medium = {"billing_dispute", "update_payment_method", "change_address", "make_payment"}
        if primary_intent in high:
            return "high"
        if primary_intent in medium or any(intent in medium for intent in secondary_intents):
            return "medium"
        return "low"

    def _needs_auth(self, primary_intent: str, secondary_intents: List[str]) -> bool:
        auth_required = {
            "billing_dispute",
            "make_payment",
            "update_payment_method",
            "check_balance",
            "lost_card",
            "loan_status",
            "change_address",
        }
        intents = {primary_intent, *secondary_intents}
        return any(intent in auth_required for intent in intents)

    def _reasoning(
        self,
        primary_intent: str,
        secondary_intents: List[str],
        is_ambiguous: bool,
        missing_slots: List[str],
        next_action: str,
    ) -> str:
        pieces = [f"Primary intent detected as '{primary_intent}'."]
        if secondary_intents:
            pieces.append(f"Secondary intents detected: {', '.join(secondary_intents)}.")
        if is_ambiguous:
            pieces.append("Top intent scores are close, so confidence is ambiguous.")
        if missing_slots:
            pieces.append(f"Missing required slots: {', '.join(missing_slots)}.")
        pieces.append(f"Recommended next action is '{next_action}' based on policy and state.")
        return " ".join(pieces)
