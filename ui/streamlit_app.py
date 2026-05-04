from __future__ import annotations

import json

import requests
import streamlit as st

st.set_page_config(page_title="NLU Reasoning Orchestrator", layout="wide")
st.title("NLU Reasoning Orchestrator Demo")
st.caption("Omilia-style banking contact-centre NLU + reasoning orchestration")


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["x-api-key"] = api_key.strip()
    return headers


def load_state(api_url: str, session_id: str, headers: dict[str, str]) -> dict | None:
    response = requests.get(f"{api_url}/state/{session_id}", headers=headers, timeout=20)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()

with st.sidebar:
    st.header("Session")
    api_url = st.text_input("API URL", value="http://localhost:8001")
    api_key = st.text_input("API Key (optional)", value="", type="password")
    session_id = st.text_input("Session ID", value="demo-session-1")
    user_id = st.text_input("User ID", value="user-123")
    st.caption("Use the same session ID across turns to demonstrate multi-turn state.")

utterance = st.text_area(
    "Customer utterance",
    value="I was charged twice last month and I also need to update the card on file.",
    height=120,
)

if st.button("Analyze", type="primary"):
    payload = {"session_id": session_id, "user_id": user_id, "utterance": utterance}
    headers = build_headers(api_key)
    try:
        response = requests.post(f"{api_url}/analyze", json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        state = load_state(api_url=api_url, session_id=session_id, headers=headers)

        tab1, tab2, tab3, tab4 = st.tabs(["Decision", "NLU Candidates", "Policy + Execution", "Session State"])
        with tab1:
            st.subheader("Decision")
            st.json(data["decision"])
        with tab2:
            st.subheader("Top NLU Candidates")
            st.json(data["nlu_candidates"])
        with tab3:
            st.subheader("Policy + Execution")
            st.json(
                {
                    "policy": data["policy"],
                    "tool_results": data.get("tool_results"),
                    "latency_ms": data["latency_ms"],
                }
            )
        with tab4:
            st.subheader("Structured Session State")
            if state is None:
                st.info("No stored state found for this session yet.")
            else:
                st.json(state)
                if state.get("turn_history"):
                    st.subheader("Turn History")
                    st.table(state["turn_history"])

    except Exception as exc:
        st.error(f"Request failed: {exc}")
        st.code(json.dumps(payload, indent=2), language="json")
