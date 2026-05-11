#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-.}"
exec gunicorn apps.api_gateway.main:app   -k uvicorn.workers.UvicornWorker   --bind ${API_HOST:-127.0.0.1}:${PORT:-${API_PORT:-8400}}   --workers ${WEB_CONCURRENCY:-2}   --timeout ${WEB_TIMEOUT:-120}   --access-logfile -   --error-logfile -
