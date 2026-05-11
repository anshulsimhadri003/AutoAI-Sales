# Streamlit tester

## Run
```bash
streamlit run streamlit_app/app.py
```

## Environment variables
- `DEFAULT_API_BASE_URL` defaults to `https://[your-domain]`
- `DEFAULT_SITE_API_KEY` is optional and is passed as `X-API-Key` when provided

For same-domain production hosting, keep the UI on `/` and route `/api/*`, `/health`, and `/health/ready` to FastAPI.
