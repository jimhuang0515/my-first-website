#!/usr/bin/env bash
set -euo pipefail
cd /workspace/my-first-website
python3 -m venv .venv
.venv/bin/pip install --disable-pip-version-check --no-cache-dir -r backend/requirements.lock
cd frontend
npm ci --cache /workspace/.npm-cache --no-audit --no-fund
cd ..
docker compose up -d --wait db
.venv/bin/python scripts/init_db.py
