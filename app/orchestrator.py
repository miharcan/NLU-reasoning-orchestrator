from __future__ import annotations

import os
import re
import time
from typing import Dict, Optional

from app.adjudicator import MockLLMAdjudicator
from app.adjudicator_factory import build_adjudicator
from app.adjudicator_http import HTTPAdjudicator
from app.monitoring import DecisionMonitor
from app.nlu import FastNLU
from app.policy import PolicyEngine
from app.schemas import OrchestratorResponse
from app.state import build_state_store
from app.tools import (
    authenticate_user,
    create_dispute_case,
    update_card_on_file,
)


class NLUReasoningOrchestrator:
    def __init__(self, monitor: Optional[DecisionMonitor] = None, adjudicator=None) -> None:
        self.nlu = FastNLU()
        self.fallback_adjudicator = MockLLMAdjudicator()
        # Keep safe default path if environment-based adjudicator cannot initialize.
        if adjudicator is not None:
            self.adjudicator = adjudicator
        else:
            try:
                self.adjudicator = build_adjudicator()
            except Exception:
                self.adjudicator = self.fallback_adjudicator
        self.state_store = build_state_store()
        self.policy = PolicyEngine()
        self.monitor = monitor
        self.http_cooldown_seconds = int(os.getenv("ADJUDICATOR_HTTP_COOLDOWN_SECONDS", "180"))
        self.http_backoff_until = 0.0
        self.last_fallback_reason: Optional[str] = None

    def analyze(self, session_id: str, user_id: str, utterance: str) -> OrchestratorResponse:
        start = time.perf_counter()
        state = self.state_store.get_or_create(session_id=session_id, user_id=user_id)

        # Policy-first authentication simulation: allow explicit auth requests to set session state.
        if self._looks_like_auth_success(utterance):
            auth_result = authenticate_user(user_id=user_id)
            self.state_store.set_authenticated(session_id=session_id, value=True)
            state = self.state_store.get_or_create(session_id=session_id, user_id=user_id)
        else:
            auth_result = None

        nlu_candidates = self.nlu.detect(utterance)
        entities = self._extract_entities(utterance)

        decision = self._decide_with_fallback(
            utterance=utterance,
            candidates=nlu_candidates,
            entities=entities,
            authenticated=state.authenticated,
        )

        policy_result = self.policy.validate(decision=decision, authenticated=state.authenticated)

        tool_results: Optional[Dict[str, str | float]] = None
        if not policy_result.allowed and decision.next_action == "call_tool":
            decision.next_action = "authenticate_user"
            decision.reasoning += " Policy denied tool call, so authentication is now required."
        elif decision.next_action == "authenticate_user" and state.authenticated:
            decision.next_action = "call_tool"
            decision.reasoning += " User is already authenticated in session; proceeding to tool call."

        if decision.next_action == "call_tool" and policy_result.allowed:
            tool_results = self._execute_tools(decision.primary_intent, entities, user_id)
        elif decision.next_action == "authenticate_user" and auth_result:
            tool_results = auth_result

        state = self.state_store.update_with_decision(state=state, decision=decision, utterance=utterance)

        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        response = OrchestratorResponse(
            session_id=session_id,
            nlu_candidates=nlu_candidates,
            decision=decision,
            policy=policy_result,
            tool_results=tool_results,
            latency_ms=latency_ms,
        )
        if self.monitor is not None:
            self.monitor.record(response)
        return response

    def get_state(self, session_id: str):
        return self.state_store.get_state(session_id)

    def _decide_with_fallback(
        self,
        utterance: str,
        candidates,
        entities: Dict[str, str],
        authenticated: bool,
    ):
        now = time.time()
        self.last_fallback_reason = None
        use_circuit_breaker = isinstance(self.adjudicator, HTTPAdjudicator) and now < self.http_backoff_until
        if use_circuit_breaker:
            self.last_fallback_reason = "http_adjudicator_circuit_open"
            decision = self.fallback_adjudicator.decide(
                utterance=utterance,
                candidates=candidates,
                entities=entities,
                authenticated=authenticated,
            )
            decision.reasoning += " Fallback adjudicator used because upstream is in cooldown."
            return decision

        try:
            decision = self.adjudicator.decide(
                utterance=utterance,
                candidates=candidates,
                entities=entities,
                authenticated=authenticated,
            )
            return decision
        except Exception:
            if isinstance(self.adjudicator, HTTPAdjudicator):
                self.http_backoff_until = time.time() + self.http_cooldown_seconds
                self.last_fallback_reason = "http_adjudicator_error"
            decision = self.fallback_adjudicator.decide(
                utterance=utterance,
                candidates=candidates,
                entities=entities,
                authenticated=authenticated,
            )
            decision.reasoning += " Fallback adjudicator used because upstream was unavailable or timed out."
            return decision

    def _extract_entities(self, utterance: str) -> Dict[str, str]:
        entities: Dict[str, str] = {}
        text = utterance.lower()

        time_period_terms = ["last month", "yesterday", "today", "last week"]
        for term in time_period_terms:
            if term in text:
                entities["time_period"] = term
                break

        amount_match = re.search(r"\$\s?(\d+(?:\.\d{1,2})?)", text)
        if amount_match:
            entities["transaction_amount"] = amount_match.group(1)
            entities["payment_amount"] = amount_match.group(1)

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if date_match:
            entities["transaction_date"] = date_match.group(1)

        card_match = re.search(r"(?:ending in|last 4)\s?(\d{4})", text)
        if card_match:
            entities["card_last4"] = card_match.group(1)

        return entities

    def _execute_tools(
        self,
        primary_intent: str,
        entities: Dict[str, str],
        user_id: str,
    ) -> Dict[str, str | float]:
        if primary_intent == "billing_dispute":
            transaction_id = "TXN-UNKNOWN"
            return create_dispute_case(user_id=user_id, transaction_id=transaction_id)

        if primary_intent == "update_payment_method":
            card_last4 = entities.get("card_last4", "0000")
            return update_card_on_file(user_id=user_id, card_last4=card_last4)

        if primary_intent == "make_payment":
            amount = entities.get("payment_amount", "0")
            return {"status": "queued", "user_id": user_id, "amount": float(amount)}

        if primary_intent == "lost_card":
            return {"status": "card_blocked", "user_id": user_id}

        if primary_intent == "change_address":
            return {"status": "address_update_requested", "user_id": user_id}

        return {"status": "no_tool_executed", "user_id": user_id}

    def _looks_like_auth_success(self, utterance: str) -> bool:
        text = utterance.lower()
        auth_markers = [
            "otp",
            "code is",
            "verified",
            "authenticate me",
            "i confirm my identity",
        ]
        return any(marker in text for marker in auth_markers)
