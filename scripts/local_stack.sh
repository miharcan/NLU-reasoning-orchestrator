#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NLU_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${NLU_DIR}/.." && pwd)"
GATEWAY_DIR="${ROOT_DIR}/ollama-gateway"
STACK_DIR="${NLU_DIR}/.local-stack"
LOG_DIR="${STACK_DIR}/logs"

OLLAMA_HOST="http://127.0.0.1:11434"
OLLAMA_MODEL="tinyllama"
GATEWAY_PORT="8000"
NLU_PORT="8001"
STREAMLIT_PORT="8501"
LOCAL_STATE_BACKEND="${LOCAL_STATE_BACKEND:-in_memory}"
LOCAL_REDIS_URL="${LOCAL_REDIS_URL:-redis://localhost:6379/0}"
LOCAL_API_AUTH_ENABLED="${LOCAL_API_AUTH_ENABLED:-false}"
LOCAL_API_KEYS="${LOCAL_API_KEYS:-demo-key-1,demo-key-2}"
LOCAL_RATE_LIMIT_ENABLED="${LOCAL_RATE_LIMIT_ENABLED:-false}"
LOCAL_RATE_LIMIT_REQUESTS_PER_MINUTE="${LOCAL_RATE_LIMIT_REQUESTS_PER_MINUTE:-120}"

mkdir -p "${LOG_DIR}"

usage() {
  cat <<EOF
Usage: $0 <up|down|status>

Commands:
  up      Start full local stack (ollama, gateway, nlu api, streamlit)
  down    Stop stack processes started by this script
  status  Show process and endpoint status

Optional env vars (set before 'up'):
  LOCAL_API_AUTH_ENABLED=true|false
  LOCAL_API_KEYS="demo-key-1,demo-key-2"
  LOCAL_RATE_LIMIT_ENABLED=true|false
  LOCAL_RATE_LIMIT_REQUESTS_PER_MINUTE=120
  LOCAL_STATE_BACKEND=in_memory|redis
  LOCAL_REDIS_URL=redis://localhost:6379/0
EOF
}

pid_file() {
  echo "${STACK_DIR}/$1.pid"
}

is_running_pid() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1
}

write_pid() {
  local name="$1"
  local pid="$2"
  echo "${pid}" > "$(pid_file "${name}")"
}

read_pid() {
  local name="$1"
  local file
  file="$(pid_file "${name}")"
  if [[ -f "${file}" ]]; then
    cat "${file}"
  fi
}

start_bg() {
  local name="$1"
  local cmd="$2"
  local logfile="${LOG_DIR}/${name}.log"

  local existing
  existing="$(read_pid "${name}" || true)"
  if [[ -n "${existing}" ]] && is_running_pid "${existing}"; then
    echo "${name} already running (pid ${existing})"
    return 0
  fi

  echo "Starting ${name}..."
  nohup bash -lc "${cmd}" >"${logfile}" 2>&1 &
  local pid=$!
  write_pid "${name}" "${pid}"
  echo "${name} started (pid ${pid}, log ${logfile})"
}

stop_bg() {
  local name="$1"
  local pid
  pid="$(read_pid "${name}" || true)"
  if [[ -z "${pid}" ]]; then
    echo "${name}: no pid file"
    return 0
  fi
  if is_running_pid "${pid}"; then
    echo "Stopping ${name} (pid ${pid})..."
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 1
    if is_running_pid "${pid}"; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
  else
    echo "${name}: pid ${pid} not running"
  fi
  rm -f "$(pid_file "${name}")"
}

wait_http() {
  local url="$1"
  local label="$2"
  local timeout="${3:-60}"

  local elapsed=0
  until curl -fsS "${url}" >/dev/null 2>&1; do
    sleep 1
    elapsed=$((elapsed + 1))
    if (( elapsed >= timeout )); then
      echo "ERROR: ${label} did not become ready at ${url} within ${timeout}s"
      return 1
    fi
  done
  echo "${label} is ready at ${url}"
}

is_endpoint_up() {
  local url="$1"
  curl -fsS "${url}" >/dev/null 2>&1
}

has_route() {
  local base_url="$1"
  local route="$2"
  curl -fsS "${base_url}/openapi.json" | jq -e --arg route "$route" '.paths[$route] != null' >/dev/null 2>&1
}

ensure_venv() {
  local dir="$1"
  local req="$2"

  if [[ ! -d "${dir}/.venv" ]]; then
    echo "Creating venv in ${dir}"
    python3 -m venv "${dir}/.venv"
  fi

  # Lightweight install check every run for convenience.
  bash -lc "source '${dir}/.venv/bin/activate' && pip install -q -r '${req}'"
}

ensure_ollama_running() {
  if curl -fsS "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo "Ollama already running"
  else
    start_bg "ollama" "ollama serve"
    wait_http "${OLLAMA_HOST}/api/tags" "ollama" 90
  fi

  if ! ollama list | awk 'NR>1 {print $1}' | grep -Eq "^${OLLAMA_MODEL}(:|$)"; then
    echo "Pulling Ollama model ${OLLAMA_MODEL}..."
    ollama pull "${OLLAMA_MODEL}"
  else
    echo "Ollama model ${OLLAMA_MODEL} already present"
  fi
}

cmd_up() {
  if [[ ! -d "${GATEWAY_DIR}" ]]; then
    echo "ERROR: expected ollama-gateway sibling repo at ${GATEWAY_DIR}"
    echo "Clone or place ollama-gateway next to this repository to use the full local stack."
    exit 1
  fi

  ensure_venv "${GATEWAY_DIR}" "${GATEWAY_DIR}/requirements.txt"
  ensure_venv "${NLU_DIR}" "${NLU_DIR}/requirements.txt"
  local desired_auth
  desired_auth="$(echo "${LOCAL_API_AUTH_ENABLED}" | tr '[:upper:]' '[:lower:]')"

  ensure_ollama_running

  if is_endpoint_up "http://127.0.0.1:${GATEWAY_PORT}/health"; then
    echo "ollama-gateway already available on port ${GATEWAY_PORT}"
  else
    start_bg \
      "ollama-gateway" \
      "cd '${GATEWAY_DIR}' && source .venv/bin/activate && OLLAMA_BASE_URL=${OLLAMA_HOST} OLLAMA_MODEL=${OLLAMA_MODEL} uvicorn app.main:app --host 0.0.0.0 --port ${GATEWAY_PORT}"
    wait_http "http://127.0.0.1:${GATEWAY_PORT}/health" "ollama-gateway" 60
  fi

  if is_endpoint_up "http://127.0.0.1:${NLU_PORT}/health"; then
    if has_route "http://127.0.0.1:${NLU_PORT}" "/analyze"; then
      local current_auth
      current_auth="$(curl -fsS "http://127.0.0.1:${NLU_PORT}/config" | jq -r '.api_auth_enabled // false' | tr '[:upper:]' '[:lower:]')"
      if [[ "${current_auth}" == "${desired_auth}" ]]; then
        echo "nlu-api already available on port ${NLU_PORT} (auth=${current_auth})"
      else
        echo "nlu-api is running but auth mode differs (current=${current_auth}, desired=${desired_auth})"
        local nlu_pid
        nlu_pid="$(read_pid "nlu-api" || true)"
        if [[ -n "${nlu_pid}" ]] && is_running_pid "${nlu_pid}"; then
          stop_bg "nlu-api"
          start_bg \
            "nlu-api" \
            "cd '${NLU_DIR}' && source .venv/bin/activate && ADJUDICATOR_MODE=http ADJUDICATOR_HTTP_URL=http://127.0.0.1:${GATEWAY_PORT}/adjudicate ADJUDICATOR_HTTP_TIMEOUT_SECONDS=12 ADJUDICATOR_HTTP_COOLDOWN_SECONDS=180 API_AUTH_ENABLED=${LOCAL_API_AUTH_ENABLED} API_KEYS='${LOCAL_API_KEYS}' RATE_LIMIT_ENABLED=${LOCAL_RATE_LIMIT_ENABLED} RATE_LIMIT_REQUESTS_PER_MINUTE=${LOCAL_RATE_LIMIT_REQUESTS_PER_MINUTE} STATE_BACKEND=${LOCAL_STATE_BACKEND} REDIS_URL=${LOCAL_REDIS_URL} uvicorn app.main:app --host 0.0.0.0 --port ${NLU_PORT}"
          wait_http "http://127.0.0.1:${NLU_PORT}/health" "nlu-api" 60
        else
          echo "ERROR: nlu-api on ${NLU_PORT} is not managed by this script."
          echo "Stop process on ${NLU_PORT} manually or run '$0 down' then '$0 up'."
          exit 1
        fi
      fi
    else
      echo "ERROR: service on port ${NLU_PORT} is not the NLU API (/analyze missing)."
      echo "Run '$0 down' or stop the process on ${NLU_PORT}, then retry."
      exit 1
    fi
  else
    start_bg \
      "nlu-api" \
      "cd '${NLU_DIR}' && source .venv/bin/activate && ADJUDICATOR_MODE=http ADJUDICATOR_HTTP_URL=http://127.0.0.1:${GATEWAY_PORT}/adjudicate ADJUDICATOR_HTTP_TIMEOUT_SECONDS=12 ADJUDICATOR_HTTP_COOLDOWN_SECONDS=180 API_AUTH_ENABLED=${LOCAL_API_AUTH_ENABLED} API_KEYS='${LOCAL_API_KEYS}' RATE_LIMIT_ENABLED=${LOCAL_RATE_LIMIT_ENABLED} RATE_LIMIT_REQUESTS_PER_MINUTE=${LOCAL_RATE_LIMIT_REQUESTS_PER_MINUTE} STATE_BACKEND=${LOCAL_STATE_BACKEND} REDIS_URL=${LOCAL_REDIS_URL} uvicorn app.main:app --host 0.0.0.0 --port ${NLU_PORT}"
    wait_http "http://127.0.0.1:${NLU_PORT}/health" "nlu-api" 60
  fi

  if is_endpoint_up "http://127.0.0.1:${STREAMLIT_PORT}"; then
    echo "streamlit already available on port ${STREAMLIT_PORT}"
  else
    start_bg \
      "streamlit" \
      "cd '${NLU_DIR}' && source .venv/bin/activate && streamlit run ui/streamlit_app.py --server.port ${STREAMLIT_PORT} --server.headless true"
    wait_http "http://127.0.0.1:${STREAMLIT_PORT}" "streamlit" 60
  fi

  cat <<EOF

Local stack is up.

UI:        http://localhost:${STREAMLIT_PORT}
Gateway:   http://localhost:${GATEWAY_PORT}
NLU API:   http://localhost:${NLU_PORT}

In Streamlit sidebar set:
- API URL: http://localhost:${NLU_PORT}
Auth mode:
- API_AUTH_ENABLED=${LOCAL_API_AUTH_ENABLED}
- RATE_LIMIT_ENABLED=${LOCAL_RATE_LIMIT_ENABLED}
If auth is enabled, use Streamlit sidebar field:
- API Key: one of ${LOCAL_API_KEYS}

Useful commands:
- $0 status
- $0 down
EOF
}

cmd_down() {
  stop_bg "streamlit"
  stop_bg "nlu-api"
  stop_bg "ollama-gateway"
  stop_bg "ollama"
  echo "Local stack stopped."
}

endpoint_status() {
  local url="$1"
  local label="$2"
  if curl -fsS "${url}" >/dev/null 2>&1; then
    echo "${label}: up (${url})"
  else
    echo "${label}: down (${url})"
  fi
}

proc_status() {
  local name="$1"
  local pid
  pid="$(read_pid "${name}" || true)"
  if [[ -n "${pid}" ]] && is_running_pid "${pid}"; then
    echo "${name}: running (pid ${pid})"
  else
    echo "${name}: not running"
  fi
}

cmd_status() {
  proc_status "ollama"
  proc_status "ollama-gateway"
  proc_status "nlu-api"
  proc_status "streamlit"

  endpoint_status "${OLLAMA_HOST}/api/tags" "ollama"
  endpoint_status "http://127.0.0.1:${GATEWAY_PORT}/health" "ollama-gateway"
  endpoint_status "http://127.0.0.1:${NLU_PORT}/health" "nlu-api"
  endpoint_status "http://127.0.0.1:${STREAMLIT_PORT}" "streamlit"
}

main() {
  if [[ $# -ne 1 ]]; then
    usage
    exit 1
  fi

  case "$1" in
    up) cmd_up ;;
    down) cmd_down ;;
    status) cmd_status ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
