
import pytest

from app.adjudicator import MockLLMAdjudicator
from app.adjudicator_factory import build_adjudicator
from app.adjudicator_http import HTTPAdjudicator


def test_build_adjudicator_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADJUDICATOR_MODE", raising=False)
    adjudicator = build_adjudicator()
    assert isinstance(adjudicator, MockLLMAdjudicator)


def test_build_adjudicator_http_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJUDICATOR_MODE", "http")
    monkeypatch.delenv("ADJUDICATOR_HTTP_URL", raising=False)
    with pytest.raises(ValueError):
        build_adjudicator()


def test_build_adjudicator_http_with_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADJUDICATOR_MODE", "http")
    monkeypatch.setenv("ADJUDICATOR_HTTP_URL", "https://example.com/adjudicate")
    adjudicator = build_adjudicator()
    assert isinstance(adjudicator, HTTPAdjudicator)
