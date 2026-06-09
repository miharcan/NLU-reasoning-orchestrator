from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_state_endpoint_returns_session_state_after_analyze() -> None:
    analyze_response = client.post(
        "/analyze",
        json={
            "session_id": "state-api-1",
            "user_id": "user-1",
            "utterance": "I lost my debit card",
        },
    )
    assert analyze_response.status_code == 200
    assert analyze_response.json()["decision"]["primary_intent"] == "lost_card"

    state_response = client.get("/state/state-api-1")
    assert state_response.status_code == 200
    payload = state_response.json()

    assert payload["session_id"] == "state-api-1"
    assert payload["turn_count"] >= 1
    assert payload["turn_history"][0]["utterance"] == "I lost my debit card"


def test_state_endpoint_returns_404_for_unknown_session() -> None:
    response = client.get("/state/unknown-session-for-test")
    assert response.status_code == 404
