#!/usr/bin/env bash
set -euo pipefail
cd /workspace/my-first-website
docker compose up -d --wait db
.venv/bin/python scripts/init_db.py
backend_pid=""
frontend_pid=""
cleanup() {
  if [[ -n "$backend_pid" ]]; then kill "$backend_pid" 2>/dev/null || true; fi
  if [[ -n "$frontend_pid" ]]; then kill "$frontend_pid" 2>/dev/null || true; fi
  wait || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
backend_pid=$!
NEXT_TELEMETRY_DISABLED=1 node frontend/node_modules/next/dist/bin/next dev frontend --hostname 127.0.0.1 --port 3000 &
frontend_pid=$!
wait -n "$backend_pid" "$frontend_pid"
