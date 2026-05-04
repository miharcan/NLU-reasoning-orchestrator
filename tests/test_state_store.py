import pytest

from app.schemas import NLUDecision
from app.state import InMemoryDialogueStateStore, build_state_store


def test_build_state_store_defaults_to_in_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STATE_BACKEND", raising=False)
    store = build_state_store()
    assert isinstance(store, InMemoryDialogueStateStore)


def test_in_memory_state_store_roundtrip() -> None:
    store = InMemoryDialogueStateStore()
    state = store.get_or_create(session_id="s-1", user_id="u-1")
    assert state.session_id == "s-1"
    store.set_authenticated(session_id="s-1", value=True)
    state = store.get_or_create(session_id="s-1", user_id="u-1")
    assert state.authenticated is True


def test_state_store_tracks_turn_history() -> None:
    store = InMemoryDialogueStateStore()
    state = store.get_or_create(session_id="s-2", user_id="u-2")
    store.set_authenticated(session_id="s-2", value=True)
    state = store.get_or_create(session_id="s-2", user_id="u-2")

    updated = store.update_with_decision(
        state=state,
        decision=NLUDecision(
            primary_intent="billing_dispute",
            secondary_intents=[],
            entities={"time_period": "last month"},
            missing_slots=["transaction_amount"],
            risk_level="medium",
            next_action="ask_clarification",
            reasoning="Demo reasoning for test coverage.",
        ),
        utterance="I was charged twice last month",
    )

    assert updated.turn_count == 1
    assert updated.turn_history[0].utterance == "I was charged twice last month"
    assert updated.turn_history[0].authenticated is True
