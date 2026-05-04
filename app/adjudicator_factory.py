from __future__ import annotations

import os
from typing import Protocol

from app.adjudicator import MockLLMAdjudicator
from app.adjudicator_http import HTTPAdjudicator


class Adjudicator(Protocol):
    def decide(self, utterance, candidates, entities, authenticated):
        ...


def build_adjudicator() -> Adjudicator:
    mode = os.getenv("ADJUDICATOR_MODE", "mock").strip().lower()
    if mode == "http":
        return HTTPAdjudicator()
    return MockLLMAdjudicator()
