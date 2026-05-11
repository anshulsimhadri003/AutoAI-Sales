# Same-domain deployment guide

This package is prepared for a single public domain deployment:

- `https://[your-domain]/` -> Streamlit UI
- `https://[your-domain]/api/*` -> FastAPI
- `https://[your-domain]/health` -> FastAPI
- `https://[your-domain]/health/ready` -> FastAPI

## What is included

- `scripts/start_api.sh` for Gunicorn + Uvicorn
- `scripts/start_streamlit.sh` for Streamlit
- `scripts/verify_deploy.sh` for post-deploy checks
- `deploy/nginx/[your-domain].conf` for same-domain path routing
- `deploy/systemd/autosales-api.service` service template
- `deploy/systemd/autosales-streamlit.service` service template
- `.env.example` with production placeholders

## Server ports

- FastAPI: `127.0.0.1:8400`
- Streamlit: `127.0.0.1:8501`

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in production secrets in .env
alembic upgrade head
```

## Start services manually

```bash
./scripts/start_api.sh
./scripts/start_streamlit.sh
```

## Deploy with systemd

1. Copy the two files from `deploy/systemd/` into `/etc/systemd/system/`
2. Update `User`, `WorkingDirectory`, and `PATH`
3. Run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable autosales-api autosales-streamlit
sudo systemctl start autosales-api autosales-streamlit
```

## Nginx

1. Copy `deploy/nginx/[your-domain].conf` to your Nginx sites directory
2. Enable the site
3. Test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Verification

```bash
./scripts/verify_deploy.sh https://[your-domain]
```

Expected behavior:

- `/` renders Streamlit HTML
- `/health` returns JSON
- `/health/ready` returns JSON
- `/api/v1/*` hits FastAPI instead of Streamlit

## Important security note

The prior package contained a populated `.env` file with a real-looking API key. That file has been removed from this deployment handoff package. Fill `.env` manually on the target server.
