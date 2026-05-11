# Halcyon Auto Sales Digital Workers

This package contains:
- a FastAPI backend for leads, messaging, appointments, and dashboard routes
- a Streamlit UI for exercising the APIs
- Alembic migrations for database setup
- same-domain deployment assets for Nginx + systemd

## Main apps
- FastAPI entrypoint: `apps/api_gateway/main.py`
- Streamlit entrypoint: `streamlit_app/app.py`

## Quick setup
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
```

## Run locally
```bash
./scripts/start_api.sh
./scripts/start_streamlit.sh
```

## Same public domain deployment
- `/` -> Streamlit
- `/api/*` -> FastAPI
- `/health` -> FastAPI
- `/health/ready` -> FastAPI

See `README_DEPLOY.md` and the `deploy/` folder for ready-to-use configs.
