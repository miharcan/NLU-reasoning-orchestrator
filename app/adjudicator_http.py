from __future__ import annotations

import os
from typing import Dict, List

import requests

from app.schemas import IntentScore, NLUDecision


class HTTPAdjudicator:
    """Adjudicator that delegates reasoning to a remote HTTP LLM service."""

    def __init__(self) -> None:
        self.url = os.getenv("ADJUDICATOR_HTTP_URL", "").strip()
        self.timeout_seconds = float(os.getenv("ADJUDICATOR_HTTP_TIMEOUT_SECONDS", "20"))
        self.auth_header_name = os.getenv("ADJUDICATOR_HTTP_AUTH_HEADER", "").strip()
        self.auth_header_value = os.getenv("ADJUDICATOR_HTTP_AUTH_VALUE", "").strip()
        if not self.url:
            raise ValueError("ADJUDICATOR_HTTP_URL must be set when ADJUDICATOR_MODE=http")

    def decide(
        self,
        utterance: str,
        candidates: List[IntentScore],
        entities: Dict[str, str],
        authenticated: bool,
    ) -> NLUDecision:
        payload = {
            "utterance": utterance,
            "candidates": [c.model_dump() for c in candidates],
            "entities": entities,
            "authenticated": authenticated,
            "task": (
                "Return a strict JSON NLU decision with keys: primary_intent, "
                "secondary_intents, entities, missing_slots, risk_level, next_action, reasoning"
            ),
        }
        headers = {"Content-Type": "application/json"}
        if self.auth_header_name and self.auth_header_value:
            headers[self.auth_header_name] = self.auth_header_value

        response = requests.post(
            self.url,
            json=payload,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        body = response.json()
        decision_payload = body.get("decision", body)
        return NLUDecision.model_validate(decision_payload)
