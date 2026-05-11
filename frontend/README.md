# [YourBrand] Auto Sales AI Frontend

Modern React + TypeScript dashboard for the Sales Digital Workers backend.

## Run locally

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Default frontend URL: `http://localhost:5173`

Default backend expected by the frontend: `http://127.0.0.1:8400`

## Configure API

Edit `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8400
VITE_DEALERSHIP_ID=dealer-001
VITE_SITE_API_KEY=
```

Set `VITE_SITE_API_KEY` only if `REQUIRE_SITE_API_KEY=true` on the backend.

## Main screens

- Command Center dashboard
- Lead Inbox with scoring details and timeline drawer
- Follow-Up/Nurture sequence board
- Appointment board with show/no-show actions
- Unified Lead Event simulator
- AI Reply Lab
- Runtime worker settings
