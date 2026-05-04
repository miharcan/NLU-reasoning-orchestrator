from __future__ import annotations

import json
import logging
import os
import time

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.monitoring import DecisionMonitor
from app.orchestrator import NLUReasoningOrchestrator
from app.schemas import AnalyzeRequest, DialogueState, OrchestratorResponse
from app.security import ApiKeyAuth, build_rate_limiter

app = FastAPI(title="NLU Reasoning Orchestrator", version="1.0.0")
monitor = DecisionMonitor()
orchestrator = NLUReasoningOrchestrator(monitor=monitor)
api_key_auth = ApiKeyAuth()
rate_limiter = build_rate_limiter()

logger = logging.getLogger("nlu_orchestrator")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def _slo_targets() -> dict:
    return {
        "p95_latency_ms": float(os.getenv("SLO_P95_LATENCY_MS", "1500")),
        "fallback_rate": float(os.getenv("SLO_FALLBACK_RATE", "0.15")),
        "policy_denial_rate": float(os.getenv("SLO_POLICY_DENIAL_RATE", "0.05")),
        "json_validity_rate": float(os.getenv("SLO_JSON_VALIDITY_RATE", "0.999")),
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_and_logging(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    api_key = request.headers.get("x-api-key")
    key_identifier = api_key if api_key else f"ip:{client_ip}"

    if not api_key_auth.is_authorized(path=request.url.path, method=request.method, api_key=api_key):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    if not rate_limiter.allow(key_identifier):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    started = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
            }
        )
    )
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "nlu-reasoning-orchestrator"}


@app.get("/config")
def config() -> dict:
    return {
        "adjudicator_mode": os.getenv("ADJUDICATOR_MODE", "mock"),
        "adjudicator_http_url_set": bool(os.getenv("ADJUDICATOR_HTTP_URL")),
        "adjudicator_http_timeout_seconds": float(os.getenv("ADJUDICATOR_HTTP_TIMEOUT_SECONDS", "20")),
        "adjudicator_http_cooldown_seconds": int(os.getenv("ADJUDICATOR_HTTP_COOLDOWN_SECONDS", "180")),
        "adjudicator_http_backoff_active": bool(orchestrator.http_backoff_until > time.time()),
        "last_fallback_reason": orchestrator.last_fallback_reason,
        "state_backend": os.getenv("STATE_BACKEND", "in_memory"),
        "api_auth_enabled": api_key_auth.enabled,
        "rate_limit_enabled": rate_limiter.enabled,
        "rate_limit_requests_per_minute": rate_limiter.requests_per_minute,
    }


@app.get("/stats")
def stats() -> dict:
    return monitor.snapshot()


@app.get("/state/{session_id}", response_model=DialogueState)
def state(session_id: str) -> DialogueState:
    current_state = orchestrator.get_state(session_id)
    if current_state is None:
        raise HTTPException(status_code=404, detail="Session state not found")
    return current_state


@app.get("/slo")
def slo() -> dict:
    return monitor.slo_status(_slo_targets())


@app.get("/metrics")
def metrics() -> Response:
    snapshot = monitor.snapshot()
    lines = [
        "# HELP nlu_requests_total Total analyzed requests",
        "# TYPE nlu_requests_total counter",
        f"nlu_requests_total {snapshot['total_requests']}",
        "# HELP nlu_policy_denials_total Total policy denials",
        "# TYPE nlu_policy_denials_total counter",
        f"nlu_policy_denials_total {snapshot['policy_denials']}",
        "# HELP nlu_avg_latency_ms Average service latency in milliseconds",
        "# TYPE nlu_avg_latency_ms gauge",
        f"nlu_avg_latency_ms {snapshot['avg_latency_ms']}",
        "# HELP nlu_multi_intent_rate Multi-intent response rate",
        "# TYPE nlu_multi_intent_rate gauge",
        f"nlu_multi_intent_rate {snapshot['multi_intent_rate']}",
        "# HELP nlu_fallback_rate Clarification fallback response rate",
        "# TYPE nlu_fallback_rate gauge",
        f"nlu_fallback_rate {snapshot['fallback_rate']}",
    ]
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.post("/analyze", response_model=OrchestratorResponse)
def analyze(req: AnalyzeRequest) -> OrchestratorResponse:
    return orchestrator.analyze(
        session_id=req.session_id,
        user_id=req.user_id,
        utterance=req.utterance,
    )
