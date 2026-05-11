# [YourBrand] Auto Sales Digital Workers

Production-style backend + modern React frontend for the Sales Digital Workers project.

## What changed in this package

- Removed real `.env` from the repository package and replaced it with a safe `.env.example`.
- Disabled FAISS by default and made FAISS import lazy to avoid local/deployment hangs on unsupported systems.
- Added session-event replay: anonymous website events are now attached to the lead and rescored when `CREATE_LEAD` is submitted.
- Added lead timeline, score-breakdown, manual response registration, and manual reassignment APIs.
- Added appointment show/no-show APIs.
- Added dashboard overview API for the React dashboard.
- Added a modern interactive React + TypeScript frontend under `frontend/`.
- Kept the existing Streamlit app as an optional internal API playground.

## Backend setup

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
```

## Run backend on port 8400

```bash
uvicorn apps.api_gateway.main:app --reload --host 127.0.0.1 --port 8400
```

or:

```bash
./scripts/start_api_8400.sh
```

## Run React frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

Backend expected by frontend: `http://127.0.0.1:8400`

## Optional Streamlit playground

```bash
streamlit run streamlit_app/app.py --server.port 8501
```

## Main backend APIs

```text
GET  /health
GET  /api/v1/workers
GET  /api/v1/dashboard/overview
GET  /api/v1/leads
POST /api/v1/leads
GET  /api/v1/leads/{lead_id}/timeline
GET  /api/v1/leads/{lead_id}/score-breakdown
POST /api/v1/leads/{lead_id}/respond
POST /api/v1/leads/{lead_id}/assign
POST /api/lead/event
GET  /api/lead/event/session/{session_id}
GET  /api/v1/sequences
POST /api/v1/messages/reply
GET  /api/v1/appointments
GET  /api/v1/appointments/slots
POST /api/v1/appointments/book
POST /api/v1/appointments/reschedule
POST /api/v1/appointments/{appointment_id}/mark-show
POST /api/v1/appointments/{appointment_id}/mark-no-show
```

## Important security note

Any key that was previously present in `.env` or `.env.example` should be considered exposed and rotated before production use.

## Optional FAISS semantic acceleration

FAISS is now optional. Install it only after confirming platform compatibility:

```bash
pip install -r requirements-optional.txt
# then set SEMANTIC_FAISS_ENABLED=true in .env
```
