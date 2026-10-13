#!/usr/bin/env bash
set -euo pipefail
cd /workspace/my-first-website
docker compose up -d --wait db
.venv/bin/python scripts/init_db.py
container_name="stocklab-e2e-$$"
cleanup() { docker rm -f "$container_name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 130' INT TERM
docker run -d --name "$container_name" --network my-first-website_default \
  -p 127.0.0.1:13000:10000 \
  -e DATABASE_URL=postgresql+psycopg://stockdev:stockdev@db:5432/stocktest \
  -e STOCK_DATA_MODE=demo -e COOKIE_SECURE=false -e APP_ORIGIN=http://127.0.0.1:13000 \
  taiwan-stock-lab:deployment >/dev/null
.venv/bin/python - <<'PY'
import time,urllib.request,json
for attempt in range(60):
    try:
        with urllib.request.urlopen('http://127.0.0.1:13000/api/v1/health',timeout=2) as r:
            body=json.load(r)
            assert body['database']=='postgresql' and body['data_mode']=='demo'
        break
    except Exception:
        if attempt==59:raise SystemExit('Container did not become ready.')
        time.sleep(.5)
PY
cd frontend
npx --no-install playwright test
