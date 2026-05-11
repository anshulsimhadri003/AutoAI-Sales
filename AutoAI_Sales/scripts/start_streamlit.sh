#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-.}"
exec streamlit run streamlit_app/app.py   --server.address "${STREAMLIT_HOST:-127.0.0.1}"   --server.port "${STREAMLIT_PORT:-8501}"
