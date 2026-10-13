#!/usr/bin/env bash
set -euo pipefail
cd /app
backend_pid=""
frontend_pid=""
cleanup() {
  if [[ -n "$backend_pid" ]]; then kill "$backend_pid" 2>/dev/null || true; fi
  if [[ -n "$frontend_pid" ]]; then kill "$frontend_pid" 2>/dev/null || true; fi
  wait || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
backend_pid=$!
python - <<'PY'
import time, urllib.request
for attempt in range(60):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=2) as response:
            assert response.status==200
        break
    except Exception:
        if attempt==59: raise SystemExit('Backend/database did not become ready.')
        time.sleep(.5)
PY
cd frontend
PORT="${PORT:-10000}" HOSTNAME=0.0.0.0 node server.js &
frontend_pid=$!
wait -n "$backend_pid" "$frontend_pid"
