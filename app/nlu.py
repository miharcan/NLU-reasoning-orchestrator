from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Set

from app.schemas import IntentScore

INTENT_EXAMPLES: Dict[str, List[str]] = {
    "billing_dispute": [
        "i was charged twice",
        "there is a wrong charge on my account",
        "my bill amount is incorrect",
        "i need to dispute a transaction",
    ],
    "make_payment": [
        "i want to pay my bill",
        "make a payment today",
        "pay my credit card",
        "can i settle my balance now",
    ],
    "update_payment_method": [
        "update the card on file",
        "change my payment method",
        "replace old debit card for autopay",
        "add a new card",
    ],
    "check_balance": [
        "what is my account balance",
        "check my balance",
        "how much do i owe",
    ],
    "lost_card": [
        "i lost my debit card",
        "my card was stolen",
        "block my credit card",
    ],
    "loan_status": [
        "what is my loan status",
        "check mortgage application",
        "any update on my loan",
    ],
    "change_address": [
        "i need to change my address",
        "update mailing address",
        "my home address changed",
    ],
    "speak_to_agent": [
        "let me talk to a person",
        "i need a human agent",
        "connect me to support",
    ],
}

TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")


class FastNLU:
    def __init__(self) -> None:
        self.intent_centroids = {
            intent: self._centroid(samples)
            for intent, samples in INTENT_EXAMPLES.items()
        }

    def detect(self, utterance: str, top_k: int = 3) -> List[IntentScore]:
        utterance_vec = self._vectorize(utterance)
        if not utterance_vec:
            return [IntentScore(intent="speak_to_agent", confidence=0.35)]

        scored = []
        for intent, centroid in self.intent_centroids.items():
            similarity = self._cosine(utterance_vec, centroid)
            keyword_boost = self._keyword_boost(intent, utterance.lower())
            score = min(1.0, max(0.0, similarity + keyword_boost))
            scored.append(IntentScore(intent=intent, confidence=round(score, 3)))

        scored.sort(key=lambda x: x.confidence, reverse=True)
        return scored[:top_k]

    def _centroid(self, samples: List[str]) -> Counter:
        vectors = [self._vectorize(sample) for sample in samples]
        centroid = Counter()
        for vec in vectors:
            centroid.update(vec)
        if vectors:
            for key in list(centroid.keys()):
                centroid[key] /= len(vectors)
        return centroid

    def _vectorize(self, text: str) -> Counter:
        tokens = [t.lower() for t in TOKEN_RE.findall(text)]
        return Counter(tokens)

    def _cosine(self, a: Counter, b: Counter) -> float:
        shared = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in shared)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _keyword_boost(self, intent: str, utterance: str) -> float:
        boost_rules: Dict[str, Set[str]] = {
            "billing_dispute": {"charged", "wrong", "dispute", "double", "twice", "incorrect"},
            "make_payment": {"pay", "payment", "settle"},
            "update_payment_method": {"update card", "card on file", "payment method", "new card"},
            "check_balance": {"balance", "owe"},
            "lost_card": {"lost", "stolen", "block card"},
            "loan_status": {"loan", "mortgage", "application"},
            "change_address": {"address", "mailing"},
            "speak_to_agent": {"agent", "human", "person", "representative"},
        }
        terms = boost_rules[intent]
        return 0.2 if any(term in utterance for term in terms) else 0.0
