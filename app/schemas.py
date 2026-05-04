from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

SUPPORTED_INTENTS = {
    "billing_dispute",
    "make_payment",
    "update_payment_method",
    "check_balance",
    "lost_card",
    "loan_status",
    "change_address",
    "speak_to_agent",
}

SUPPORTED_ACTIONS = {
    "answer",
    "ask_clarification",
    "authenticate_user",
    "call_tool",
    "escalate",
}


class AnalyzeRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    utterance: str = Field(..., min_length=2)


class IntentScore(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class NLUDecision(BaseModel):
    primary_intent: str
    secondary_intents: List[str] = Field(default_factory=list)
    entities: Dict[str, str] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    next_action: str
    reasoning: str = Field(..., min_length=10)


class PolicyResult(BaseModel):
    allowed: bool
    reason: str


class ToolCall(BaseModel):
    name: str
    payload: Dict[str, str | float]


class TurnRecord(BaseModel):
    turn_index: int = Field(..., ge=1)
    utterance: str
    primary_intent: str
    next_action: str
    authenticated: bool
    missing_slots: List[str] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    session_id: str
    nlu_candidates: List[IntentScore]
    decision: NLUDecision
    policy: PolicyResult
    tool_results: Optional[Dict[str, str | float]] = None
    latency_ms: float


class DialogueState(BaseModel):
    session_id: str
    user_id: str
    authenticated: bool = False
    current_intent: Optional[str] = None
    collected_slots: Dict[str, str] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    risk_level: str = "low"
    turn_count: int = 0
    turn_history: List[TurnRecord] = Field(default_factory=list)
