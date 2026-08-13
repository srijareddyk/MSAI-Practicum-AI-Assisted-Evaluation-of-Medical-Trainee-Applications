#!/usr/bin/env bash
# Start API + Vite frontend for local development.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

echo "Starting API on http://127.0.0.1:8000 ..."
python -m uvicorn api.server:app --reload --host 127.0.0.1 --port 8000 &
API_PID=$!

cleanup() {
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Starting frontend on http://127.0.0.1:5173 ..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
