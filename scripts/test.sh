#!/usr/bin/env bash
set -euo pipefail
cd /workspace/my-first-website
docker compose up -d --wait db
.venv/bin/python scripts/init_db.py
cd backend
../.venv/bin/pytest -q
cd ../frontend
npm run typecheck
npm run build
