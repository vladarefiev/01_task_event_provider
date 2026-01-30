#!/bin/bash
set -e

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/src"

exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
