from __future__ import annotations

import os
from typing import Dict, Protocol

from app.schemas import DialogueState, NLUDecision, TurnRecord


class DialogueStateStoreProtocol(Protocol):
    def get_or_create(self, session_id: str, user_id: str) -> DialogueState:
        ...

    def update_with_decision(self, state: DialogueState, decision: NLUDecision, utterance: str) -> DialogueState:
        ...

    def set_authenticated(self, session_id: str, value: bool) -> None:
        ...

    def get_state(self, session_id: str) -> DialogueState | None:
        ...


class InMemoryDialogueStateStore:
    def __init__(self) -> None:
        self._store: Dict[str, DialogueState] = {}

    def get_or_create(self, session_id: str, user_id: str) -> DialogueState:
        state = self._store.get(session_id)
        if state is None:
            state = DialogueState(session_id=session_id, user_id=user_id)
            self._store[session_id] = state
        return state

    def update_with_decision(self, state: DialogueState, decision: NLUDecision, utterance: str) -> DialogueState:
        state.turn_count += 1
        state.current_intent = decision.primary_intent
        state.collected_slots.update(decision.entities)
        state.missing_slots = decision.missing_slots
        state.risk_level = decision.risk_level
        state.turn_history.append(
            TurnRecord(
                turn_index=state.turn_count,
                utterance=utterance,
                primary_intent=decision.primary_intent,
                next_action=decision.next_action,
                authenticated=state.authenticated,
                missing_slots=list(decision.missing_slots),
            )
        )
        return state

    def set_authenticated(self, session_id: str, value: bool) -> None:
        if session_id in self._store:
            self._store[session_id].authenticated = value

    def get_state(self, session_id: str) -> DialogueState | None:
        return self._store.get(session_id)


class RedisDialogueStateStore:
    def __init__(self, redis_url: str, key_prefix: str = "dialogue", ttl_seconds: int = 86400) -> None:
        from redis import Redis  # lazy import so in-memory mode has no hard runtime dependency

        self.client = Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds

    def _key(self, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}"

    def _load(self, session_id: str) -> DialogueState | None:
        payload = self.client.get(self._key(session_id))
        if not payload:
            return None
        return DialogueState.model_validate_json(payload)

    def _save(self, state: DialogueState) -> None:
        self.client.set(self._key(state.session_id), state.model_dump_json(), ex=self.ttl_seconds)

    def get_or_create(self, session_id: str, user_id: str) -> DialogueState:
        state = self._load(session_id)
        if state is not None:
            return state

        state = DialogueState(session_id=session_id, user_id=user_id)
        self._save(state)
        return state

    def update_with_decision(self, state: DialogueState, decision: NLUDecision, utterance: str) -> DialogueState:
        state.turn_count += 1
        state.current_intent = decision.primary_intent
        state.collected_slots.update(decision.entities)
        state.missing_slots = decision.missing_slots
        state.risk_level = decision.risk_level
        state.turn_history.append(
            TurnRecord(
                turn_index=state.turn_count,
                utterance=utterance,
                primary_intent=decision.primary_intent,
                next_action=decision.next_action,
                authenticated=state.authenticated,
                missing_slots=list(decision.missing_slots),
            )
        )
        self._save(state)
        return state

    def set_authenticated(self, session_id: str, value: bool) -> None:
        state = self._load(session_id)
        if state is None:
            return
        state.authenticated = value
        self._save(state)

    def get_state(self, session_id: str) -> DialogueState | None:
        return self._load(session_id)


def build_state_store() -> DialogueStateStoreProtocol:
    backend = os.getenv("STATE_BACKEND", "in_memory").strip().lower()
    if backend == "redis":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        key_prefix = os.getenv("REDIS_STATE_KEY_PREFIX", "dialogue")
        ttl_seconds = int(os.getenv("REDIS_STATE_TTL_SECONDS", "86400"))
        return RedisDialogueStateStore(
            redis_url=redis_url,
            key_prefix=key_prefix,
            ttl_seconds=ttl_seconds,
        )
    return InMemoryDialogueStateStore()
