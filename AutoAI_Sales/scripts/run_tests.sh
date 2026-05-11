#!/usr/bin/env bash
set -euo pipefail
export APP_ENV=test
export DATABASE_URL=${DATABASE_URL:-sqlite:///./test_halcyon_auto_sales.db}
pytest -q
