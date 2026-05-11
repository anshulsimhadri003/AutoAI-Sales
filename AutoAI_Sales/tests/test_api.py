import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

Path("test_halcyon_auto_sales.db").unlink(missing_ok=True)
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_halcyon_auto_sales.db")
os.environ.setdefault("ENABLE_OPENAI", "false")
os.environ.setdefault("EMAIL_NOTIFICATIONS_ENABLED", "false")

from fastapi.testclient import TestClient

from apps.api_gateway.main import app
from shared.integrations.email_client import EmailClient

headers = {"X-Dealership-ID": "dealer-001"}


def make_client():
    return TestClient(app)


def test_health():
    with make_client() as client:
        response = client.get("/health")
        assert response.status_code == 200


def test_list_workers():
    with make_client() as client:
        response = client.get("/api/v1/workers", headers=headers)
        assert response.status_code == 200
        assert len(response.json()) == 3


def test_create_and_list_lead_semantic_features():
    with make_client() as client:
        payload = {
            "source_channel": "website_form",
            "first_name": "Anshul",
            "last_name": "Simhadri",
            "email": "anshul@example.com",
            "phone": "+919999999999",
            "vehicle_interest": "Honda City ZX",
            "message": "Can I book a test drive today and discuss finance options?",
            "customer_location": "Hyderabad",
        }
        created = client.post("/api/v1/leads", headers=headers, json=payload)
        assert created.status_code == 201
        lead = created.json()
        assert lead["temperature"] in {"Hot", "Warm", "Cold"}
        assert isinstance(lead["semantic_intent"], str) and lead["semantic_intent"]
        assert isinstance(lead["urgency"], str) and lead["urgency"]
        assert lead["assigned_rep"] != "Unassigned"
        assert "intent_signals" in lead
        assert lead["intent_signals"]["test_drive_interest"] is True

        listed = client.get("/api/v1/leads", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) >= 1


def test_duplicate_lead_merges_instead_of_creating_new_record():
    with make_client() as client:
        payload = {
            "source_channel": "website_form",
            "first_name": "Priya",
            "last_name": "Nair",
            "email": "priya@example.com",
            "phone": "+919999999998",
            "vehicle_interest": "Hyundai Creta SX",
            "message": "I want to move quickly if this one fits my budget.",
            "intent_signals": {
                "page_views": 8,
                "vehicle_page_time_seconds": 480,
                "chat_interactions": 3,
                "financing_inquiries": 1,
                "trade_in_requests": 1,
                "test_drive_interest": True,
            },
        }
        first = client.post("/api/v1/leads", headers=headers, json=payload)
        assert first.status_code == 201
        first_lead = first.json()

        second = client.post(
            "/api/v1/leads",
            headers=headers,
            json={**payload, "message": "Checking again. Can I get finance and trade-in help too?"},
        )
        assert second.status_code == 201
        second_lead = second.json()
        assert second_lead["public_id"] == first_lead["public_id"]
        assert second_lead["dedup_status"] == "merged"
        assert second_lead["merged_count"] >= 1


def test_reply_grounds_on_templates_and_updates_sequence():
    with make_client() as client:
        lead_payload = {
            "source_channel": "website_form",
            "first_name": "Rahul",
            "last_name": "Sharma",
            "email": "rahul@example.com",
            "phone": "+919999999997",
            "vehicle_interest": "Maruti Grand Vitara",
            "message": "Can I book a test drive and discuss finance options for my trade-in?",
        }
        created = client.post("/api/v1/leads", headers=headers, json=lead_payload)
        assert created.status_code == 201
        lead = created.json()

        response = client.post(
            "/api/v1/messages/reply",
            headers=headers,
            json={"lead_id": lead["public_id"], "message": "Can I come tomorrow evening for a test drive?"},
        )
        assert response.status_code == 200
        assert isinstance(response.json()["reply"], str)
        assert len(response.json()["reply"]) > 10

        sequences = client.get("/api/v1/sequences", headers=headers)
        assert sequences.status_code == 200
        assert any(seq["lead_public_id"] == lead["public_id"] for seq in sequences.json())


def test_appointments_slots_and_booking_with_email_hook(monkeypatch):
    sent = []

    def fake_send(self, lead, appointment):
        sent.append(
            {
                "email": lead.email,
                "lead_id": lead.public_id,
                "appointment_id": appointment.public_id,
            }
        )

    monkeypatch.setattr(EmailClient, "send_appointment_confirmation", fake_send)

    lead_payload = {
        "source_channel": "website_form",
        "first_name": "Asha",
        "last_name": "Reddy",
        "email": "asha@example.com",
        "phone": "+919999999996",
        "vehicle_interest": "Kia Seltos GTX",
        "message": "I want to book a showroom appointment this week.",
    }
    with make_client() as client:
        created_lead = client.post("/api/v1/leads", headers=headers, json=lead_payload)
        assert created_lead.status_code == 201
        lead = created_lead.json()

        slots = client.get("/api/v1/appointments/slots?vehicle_id=VH-001&date=2026-04-14", headers=headers)
        assert slots.status_code == 200
        assert len(slots.json()) >= 1

        appointment_payload = {
            "lead_id": lead["public_id"],
            "vehicle_id": "VH-001",
            "rep_id": "REP-001",
            "start_time": "2026-04-14T11:00:00",
            "end_time": "2026-04-14T12:00:00",
            "channel": "email",
        }
        booked = client.post("/api/v1/appointments/book", headers=headers, json=appointment_payload)
        assert booked.status_code == 201
        appointment = booked.json()
        assert appointment["lead_id"] == lead["public_id"]
        assert appointment["status"] == "Confirmed"
        assert appointment["vehicle_status"] == "available"

        assert sent == [
            {
                "email": "asha@example.com",
                "lead_id": lead["public_id"],
                "appointment_id": appointment["public_id"],
            }
        ]


def test_unavailable_vehicle_returns_alternatives_hint():
    with make_client() as client:
        lead_payload = {
            "source_channel": "website_form",
            "first_name": "Vikram",
            "last_name": "Rao",
            "email": "vikram@example.com",
            "phone": "+919999999995",
            "vehicle_interest": "Hyundai Creta SX(O)",
            "message": "Please book the reserved SUV for me tomorrow.",
        }
        lead = client.post("/api/v1/leads", headers=headers, json=lead_payload).json()
        response = client.post(
            "/api/v1/appointments/book",
            headers=headers,
            json={
                "lead_id": lead["public_id"],
                "vehicle_id": "VH-029",
                "rep_id": "REP-001",
                "start_time": "2026-04-14T12:00:00",
                "end_time": "2026-04-14T13:00:00",
                "channel": "email",
            },
        )
        assert response.status_code == 409
        assert "Suggested alternatives" in response.json()["detail"]


def test_generic_capability_reply_without_lead_context():
    with make_client() as client:
        response = client.post(
            "/api/v1/messages/reply",
            headers=headers,
            json={"message": "What can you do?"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"].lower()
        assert "pricing" in reply
        assert "test drive" in reply
        assert "appointments" in reply


def test_greeting_reply_without_lead_context():
    with make_client() as client:
        response = client.post(
            "/api/v1/messages/reply",
            headers=headers,
            json={"message": "Hi"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"].lower()
        assert reply.startswith("hi")
        assert "finance" in reply


def test_unified_lead_event_create_lead():
    with make_client() as client:
        payload = {
            "action": "CREATE_LEAD",
            "sessionId": "5cde115d-682e-44e8-ad00-dc065407cbf3",
            "data": {
                "Name": "Rakesh P",
                "PhoneNumber": "919573069795",
                "Email": "rakesh.p@halcyontek.com",
                "Address": "Hyderabad",
                "SessionId": "5cde115d-682e-44e8-ad00-dc065407cbf3",
                "VehicleId": 1383266,
                "VehicleName": "Tesla Model Y",
                "Vin": "5YJYGDEE8MF123456",
                "Year": "2025",
                "Make": "Tesla",
                "Model": "Model Y",
                "Message": "Interested in test drive",
            },
        }
        response = client.post("/api/lead/event", headers=headers, json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["action"] == "CREATE_LEAD"
        assert body["sessionId"] == payload["sessionId"]
        assert body["lead"]["vehicle_interest"] == "Tesla Model Y"
        assert body["lead"]["intent_signals"]["test_drive_interest"] is True
        assert body["leadPublicId"]


def test_unified_lead_event_tracks_session_and_refreshes_score():
    with make_client() as client:
        session_id = "a6c554c6-26f9-40af-9237-c82b28ea2d9e"
        create_payload = {
            "action": "CREATE_LEAD",
            "sessionId": session_id,
            "data": {
                "Name": "Sneha R",
                "PhoneNumber": "919111111111",
                "Email": "sneha.r@example.com",
                "Address": "Hyderabad",
                "SessionId": session_id,
                "VehicleId": 1001,
                "VehicleName": "Hyundai Creta",
                "Vin": "MA1AB2CD3EF456789",
                "Year": "2025",
                "Make": "Hyundai",
                "Model": "Creta",
                "Message": "Just exploring options",
            },
        }
        created = client.post("/api/lead/event", headers=headers, json=create_payload)
        assert created.status_code == 201
        base_score = created.json()["lead"]["score"]

        track_payload = {
            "action": "TRACK_EVENT",
            "sessionId": session_id,
            "eventType": "INVENTORY_DWELL_TIME",
            "data": {
                "durationSeconds": 240,
                "VehicleName": "Hyundai Creta",
                "Message": "Can I schedule a test drive and finance discussion this week?",
            },
        }
        tracked = client.post("/api/lead/event", headers=headers, json=track_payload)
        assert tracked.status_code == 201
        body = tracked.json()
        assert body["eventType"] == "INVENTORY_DWELL_TIME"
        assert body["lead"]["score"] >= base_score
        assert body["lead"]["intent_signals"]["vehicle_page_time_seconds"] >= 240
        assert body["lead"]["intent_signals"]["test_drive_interest"] is True
