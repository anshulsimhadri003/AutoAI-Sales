# Deployment upgrade summary

## What changed
- Refactored the system into **LangGraph-driven agent workflows** for:
  - lead intake
  - reply generation
  - appointment booking
  - appointment rescheduling
- Replaced pure cosine-only retrieval with **FAISS + hybrid lexical/semantic scoring**.
- Added live-deployment support files:
  - `.env.example`
  - `Procfile`
  - `scripts/start_api.sh`
  - `scripts/run_tests.sh`
  - `README_DEPLOY.md`
- Hardened startup and runtime behavior:
  - app factory with lifespan startup
  - request-id middleware
  - gzip middleware
  - trusted-host support
  - optional `X-API-Key` protection for public endpoints
- Switched public ID generation to UUID-based IDs instead of count-based IDs.
- Added readiness endpoint: `/health/ready`.
- Added Alembic migration `0003_expand_schema_for_live_deploy.py` to better align migrations with the current model set.

## Validation
- Syntax compiled successfully.
- Test suite result: **9 passed**.

## Deferred by request
External calendar, email, and messaging integrations were intentionally left as non-blocking/demo-safe stubs for now.
