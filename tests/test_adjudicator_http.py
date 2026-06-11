import pytest
from pydantic import ValidationError

from app.adjudicator_http import HTTPAdjudicator, HTTPAdjudicatorResponseError
from app.schemas import IntentScore


class FakeResponse:
    def __init__(self, body: dict) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.body


def _candidate() -> IntentScore:
    return IntentScore(intent="check_balance", confidence=0.9)


def test_http_adjudicator_sends_generated_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_payload = {}

    def fake_post(url, json, headers, timeout):
        captured_payload.update(json)
        return FakeResponse(
            {
                "decision": {
                    "primary_intent": "check_balance",
                    "secondary_intents": [],
                    "entities": {},
                    "missing_slots": [],
                    "risk_level": "low",
                    "next_action": "authenticate_user",
                    "reasoning": "Balance requests require authentication before answering.",
                }
            }
        )

    monkeypatch.setenv("ADJUDICATOR_HTTP_URL", "https://example.com/adjudicate")
    monkeypatch.setattr("app.adjudicator_http.requests.post", fake_post)

    adjudicator = HTTPAdjudicator()
    decision = adjudicator.decide(
        utterance="I want to check my balance",
        candidates=[_candidate()],
        entities={},
        authenticated=False,
    )

    assert decision.primary_intent == "check_balance"
    assert "response_schema" in captured_payload
    assert captured_payload["response_schema"]["properties"]["primary_intent"]["enum"]
    assert captured_payload["response_schema"]["properties"]["next_action"]["enum"]
    assert captured_payload["response_schema"]["properties"]["risk_level"]["enum"] == [
        "low",
        "medium",
        "high",
    ]


def test_http_adjudicator_raises_on_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url, json, headers, timeout):
        return FakeResponse({"refusal": "Cannot safely adjudicate this request."})

    monkeypatch.setenv("ADJUDICATOR_HTTP_URL", "https://example.com/adjudicate")
    monkeypatch.setattr("app.adjudicator_http.requests.post", fake_post)

    adjudicator = HTTPAdjudicator()

    with pytest.raises(HTTPAdjudicatorResponseError):
        adjudicator.decide(
            utterance="I want to check my balance",
            candidates=[_candidate()],
            entities={},
            authenticated=False,
        )


def test_http_adjudicator_raises_on_invalid_decision_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url, json, headers, timeout):
        return FakeResponse(
            {
                "decision": {
                    "primary_intent": "unsupported_intent",
                    "secondary_intents": [],
                    "entities": {},
                    "missing_slots": [],
                    "risk_level": "low",
                    "next_action": "authenticate_user",
                    "reasoning": "This should fail schema validation.",
                }
            }
        )

    monkeypatch.setenv("ADJUDICATOR_HTTP_URL", "https://example.com/adjudicate")
    monkeypatch.setattr("app.adjudicator_http.requests.post", fake_post)

    adjudicator = HTTPAdjudicator()

    with pytest.raises(ValidationError):
        adjudicator.decide(
            utterance="I want to check my balance",
            candidates=[_candidate()],
            entities={},
            authenticated=False,
        )


def test_http_adjudicator_raises_on_invalid_secondary_intent(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url, json, headers, timeout):
        return FakeResponse(
            {
                "decision": {
                    "primary_intent": "check_balance",
                    "secondary_intents": ["wire_transfer"],
                    "entities": {},
                    "missing_slots": [],
                    "risk_level": "low",
                    "next_action": "authenticate_user",
                    "reasoning": "Unsupported secondary intents should fail schema validation.",
                }
            }
        )

    monkeypatch.setenv("ADJUDICATOR_HTTP_URL", "https://example.com/adjudicate")
    monkeypatch.setattr("app.adjudicator_http.requests.post", fake_post)

    adjudicator = HTTPAdjudicator()

    with pytest.raises(ValidationError):
        adjudicator.decide(
            utterance="I want to check my balance",
            candidates=[_candidate()],
            entities={},
            authenticated=False,
        )
