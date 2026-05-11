#!/usr/bin/env bash
set -euo pipefail

PUBLIC_BASE_URL="${1:-https://[your-domain]}"
API_LOCAL_URL="${2:-http://127.0.0.1:8400}"
STREAMLIT_LOCAL_URL="${3:-http://127.0.0.1:8501}"

printf '
== Local FastAPI health ==
'
curl -fsS "$API_LOCAL_URL/health" && printf '
'

printf '
== Local Streamlit landing page ==
'
curl -I -fsS "$STREAMLIT_LOCAL_URL" | sed -n '1,10p'

printf '
== Public health endpoint ==
'
curl -fsS "$PUBLIC_BASE_URL/health" && printf '
'

printf '
== Public ready endpoint ==
'
curl -fsS "$PUBLIC_BASE_URL/health/ready" && printf '
'

printf '
== Public API route headers ==
'
curl -I -fsS "$PUBLIC_BASE_URL/api/v1/workers" | sed -n '1,20p'
