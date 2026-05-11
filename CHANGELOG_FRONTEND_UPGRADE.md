# Frontend + Functional Gap Upgrade

## Security/stability
- Removed `.env` from the distributable project.
- Sanitized `.env.example` and removed hardcoded real API key values.
- Removed mandatory `faiss-cpu` from base requirements.
- Added `requirements-optional.txt` for FAISS.
- Made FAISS import lazy in `hybrid_search.py`.
- Set `SEMANTIC_FAISS_ENABLED=false` by default.

## Agent-1 Lead Qualification & Routing
- Added anonymous session replay into final lead scoring when `CREATE_LEAD` is submitted.
- Added lead timeline API: `GET /api/v1/leads/{lead_id}/timeline`.
- Added score explainability API: `GET /api/v1/leads/{lead_id}/score-breakdown`.
- Added manual agent response registration API: `POST /api/v1/leads/{lead_id}/respond`.
- Added manual lead reassignment API: `POST /api/v1/leads/{lead_id}/assign`.
- Added session event inspection API: `GET /api/lead/event/session/{session_id}`.

## Agent-2 Follow-Up & Nurture
- React frontend now surfaces sequence status, cadence, progress, pause/escalation state and engagement metadata.
- AI Reply Lab added for generating and registering outbound replies.

## Agent-3 Appointment Scheduling
- Added show/no-show tracking APIs:
  - `POST /api/v1/appointments/{appointment_id}/mark-show`
  - `POST /api/v1/appointments/{appointment_id}/mark-no-show`
- React appointment board now supports show/no-show updates.

## Dashboards
- Added `GET /api/v1/dashboard/overview` for frontend dashboard aggregation.
- Expanded lead, sequence and appointment metric payloads.

## React frontend
- Added modern React + TypeScript + Vite frontend in `frontend/`.
- Screens added:
  - Command Center
  - Lead Inbox
  - Lead detail drawer with timeline and score breakdown
  - Nurture sequence board
  - Appointment board
  - Unified Lead Event simulator
  - AI Reply Lab
  - Runtime settings/worker configuration
