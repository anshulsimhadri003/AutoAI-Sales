from __future__ import annotations

from sqlalchemy.orm import Session

from shared.models.models import (
    Dealership,
    DealershipRule,
    RepAvailability,
    SalesRep,
    SequenceDefinition,
    SequenceStepDefinition,
    StoreHour,
    VehicleInventory,
    WorkerConfig,
)
from shared.utils.csv_loader import bool_from_str, int_from_str, list_from_str, load_csv, text_or_none


WORKER_DEFINITIONS = (
    {
        "worker_key": "lead_qualification_routing",
        "name": "AI Lead Qualification & Routing Agent",
        "status": "active",
        "tagline": "No-Lead-Left-Behind",
        "description": "Captures, scores, deduplicates, enriches, and routes inbound leads.",
    },
    {
        "worker_key": "followup_nurture",
        "name": "Follow-Up & Nurture Agent",
        "status": "active",
        "tagline": "Human-sounding, disciplined",
        "description": "Runs adaptive multi-step follow-up using semantic classification and engagement tracking.",
    },
    {
        "worker_key": "appointment_orchestrator",
        "name": "Appointment Scheduling & Test-Drive Orchestrator",
        "status": "active",
        "tagline": "Inventory-Aware Scheduling",
        "description": "Coordinates slot generation, inventory checks, reminders, and rescheduling.",
    },
)


def seed_database(db: Session) -> None:
    dealership_rows = _unique_rows(load_csv("dealership_rules.csv"), key_name="dealership_id")
    _seed_dealerships(db, dealership_rows)
    _seed_dealership_rules(db, dealership_rows)
    _seed_worker_configs(db, dealership_rows)
    _seed_sales_reps(db)
    _seed_vehicles(db)
    _seed_store_hours(db)
    _seed_rep_availability(db)
    _seed_sequence_definitions(db)
    _seed_sequence_steps(db)
    db.commit()


def _seed_dealerships(db: Session, dealership_rows: list[dict[str, str]]) -> None:
    existing = {row.public_id: row for row in db.query(Dealership).all()}
    for row in dealership_rows:
        dealership_id = row.get("dealership_id", "")
        if not dealership_id:
            continue
        payload = {
            "public_id": dealership_id,
            "name": row.get("dealership_name") or dealership_id,
            "timezone": row.get("timezone") or "UTC",
            "is_active": True,
        }
        current = existing.get(dealership_id)
        if current is None:
            db.add(Dealership(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_dealership_rules(db: Session, dealership_rows: list[dict[str, str]]) -> None:
    existing = {row.dealership_id: row for row in db.query(DealershipRule).all()}
    for row in dealership_rows:
        dealership_id = row.get("dealership_id", "")
        if not dealership_id:
            continue
        payload = {
            "dealership_id": dealership_id,
            "response_sla_minutes": int_from_str(row.get("response_sla_minutes"), default=5),
            "max_leads_per_rep": int_from_str(row.get("max_leads_per_rep"), default=20),
            "allow_after_hours_booking": bool_from_str(row.get("allow_after_hours_booking"), default=False),
            "default_test_drive_duration_mins": int_from_str(row.get("default_test_drive_duration_mins"), default=30),
            "timezone": row.get("timezone") or "UTC",
        }
        current = existing.get(dealership_id)
        if current is None:
            db.add(DealershipRule(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_worker_configs(db: Session, dealership_rows: list[dict[str, str]]) -> None:
    existing = {(row.dealership_id, row.worker_key): row for row in db.query(WorkerConfig).all()}
    dealership_ids = [row["dealership_id"] for row in dealership_rows if row.get("dealership_id")]
    for dealership_id in dealership_ids:
        for definition in WORKER_DEFINITIONS:
            key = (dealership_id, definition["worker_key"])
            current = existing.get(key)
            if current is None:
                db.add(WorkerConfig(dealership_id=dealership_id, **definition))
            else:
                for field, value in definition.items():
                    setattr(current, field, value)


def _seed_sales_reps(db: Session) -> None:
    availability_hours = _availability_hour_bounds()
    existing = {row.public_id: row for row in db.query(SalesRep).all()}
    for row in load_csv("sales_reps.csv"):
        public_id = row.get("rep_id", "")
        if not public_id:
            continue
        specializations = list_from_str(row.get("vehicle_specialties"))
        languages = list_from_str(row.get("languages"))
        location = row.get("location") or "Unknown"
        start_hour, end_hour = availability_hours.get(public_id, (9, 18))
        payload = {
            "dealership_id": row.get("dealership_id", ""),
            "public_id": public_id,
            "name": row.get("rep_name", public_id),
            "email": row.get("email", ""),
            "phone": row.get("phone", ""),
            "location": location,
            "specializations": specializations,
            "languages": languages,
            "profile_text": _build_rep_profile(row.get("rep_name", public_id), specializations, location, languages),
            "workload": int_from_str(row.get("current_active_leads"), default=0),
            "max_active_leads": int_from_str(row.get("max_active_leads"), default=20),
            "is_available": bool_from_str(row.get("is_available"), default=True),
            "manager_email": text_or_none(row.get("manager_email")),
            "calendar_key": text_or_none(row.get("calendar_key")),
            "available_start_hour": start_hour,
            "available_end_hour": end_hour,
        }
        current = existing.get(public_id)
        if current is None:
            db.add(SalesRep(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_vehicles(db: Session) -> None:
    existing = {row.public_id: row for row in db.query(VehicleInventory).all()}
    for row in load_csv("vehicles.csv"):
        public_id = row.get("vehicle_id", "")
        if not public_id:
            continue
        price = int_from_str(row.get("price"), default=0)
        payload = {
            "dealership_id": row.get("dealership_id", ""),
            "public_id": public_id,
            "stock_no": text_or_none(row.get("stock_no")),
            "make_model": " ".join(part for part in [row.get("make", ""), row.get("model", "")] if part).strip(),
            "trim": row.get("variant", ""),
            "year": int_from_str(row.get("year"), default=0),
            "body_type": row.get("body_type", ""),
            "fuel_type": row.get("fuel_type", ""),
            "transmission": row.get("transmission", ""),
            "price": price,
            "price_band": _price_band(price),
            "color": row.get("color", ""),
            "location": row.get("location", ""),
            "status": row.get("status", "available"),
            "available_for_test_drive": bool_from_str(row.get("available_for_test_drive"), default=True),
            "description": row.get("description", ""),
        }
        current = existing.get(public_id)
        if current is None:
            db.add(VehicleInventory(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_store_hours(db: Session) -> None:
    existing = {(row.dealership_id, row.day_of_week): row for row in db.query(StoreHour).all()}
    for row in load_csv("store_hours.csv"):
        key = (row.get("dealership_id", ""), row.get("day_of_week", ""))
        if not all(key):
            continue
        payload = {
            "dealership_id": key[0],
            "day_of_week": key[1],
            "open_time": row.get("open_time", ""),
            "close_time": row.get("close_time", ""),
            "is_open": bool_from_str(row.get("is_open"), default=True),
            "timezone": row.get("timezone") or "UTC",
        }
        current = existing.get(key)
        if current is None:
            db.add(StoreHour(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_rep_availability(db: Session) -> None:
    existing = {
        (row.rep_id, row.date, row.start_time, row.end_time): row
        for row in db.query(RepAvailability).all()
    }
    for row in load_csv("rep_availability.csv"):
        key = (row.get("rep_id", ""), row.get("date", ""), row.get("start_time", ""), row.get("end_time", ""))
        if not all(key):
            continue
        payload = {
            "rep_id": key[0],
            "date": key[1],
            "start_time": key[2],
            "end_time": key[3],
            "status": row.get("status", "available"),
            "dealership_id": row.get("dealership_id", ""),
        }
        current = existing.get(key)
        if current is None:
            db.add(RepAvailability(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_sequence_definitions(db: Session) -> None:
    existing = {row.public_id: row for row in db.query(SequenceDefinition).all()}
    for row in load_csv("sequence_definitions.csv"):
        public_id = row.get("sequence_id", "")
        if not public_id:
            continue
        payload = {
            "public_id": public_id,
            "name": row.get("name", public_id),
            "channel": row.get("channel", "email"),
            "is_active": bool_from_str(row.get("is_active"), default=True),
            "trigger_type": row.get("trigger_type", "warm_lead"),
        }
        current = existing.get(public_id)
        if current is None:
            db.add(SequenceDefinition(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _seed_sequence_steps(db: Session) -> None:
    existing = {
        (row.sequence_public_id, row.step_order): row
        for row in db.query(SequenceStepDefinition).all()
    }
    for row in load_csv("sequence_steps.csv"):
        public_id = row.get("sequence_id", "")
        step_order = int_from_str(row.get("step_order"), default=0)
        if not public_id or step_order <= 0:
            continue
        key = (public_id, step_order)
        payload = {
            "sequence_public_id": public_id,
            "step_order": step_order,
            "delay_minutes": int_from_str(row.get("delay_minutes"), default=1440),
            "template_id": row.get("template_id", ""),
            "condition_type": row.get("condition_type", "always"),
            "condition_value": text_or_none(row.get("condition_value")),
        }
        current = existing.get(key)
        if current is None:
            db.add(SequenceStepDefinition(**payload))
        else:
            for field, value in payload.items():
                setattr(current, field, value)


def _availability_hour_bounds() -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    windows: dict[str, list[tuple[int, int]]] = {}
    for row in load_csv("rep_availability.csv"):
        if row.get("status", "").lower() != "available":
            continue
        rep_id = row.get("rep_id", "")
        if not rep_id:
            continue
        start_hour = int_from_str((row.get("start_time") or "09:00").split(":", 1)[0], default=9)
        end_hour = int_from_str((row.get("end_time") or "18:00").split(":", 1)[0], default=18)
        windows.setdefault(rep_id, []).append((start_hour, end_hour))
    for rep_id, ranges in windows.items():
        result[rep_id] = (min(start for start, _ in ranges), max(end for _, end in ranges))
    return result


def _build_rep_profile(name: str, specializations: list[str], location: str, languages: list[str]) -> str:
    specialty_text = ", ".join(specializations) or "vehicle sales"
    language_text = ", ".join(languages) or "English"
    return f"{name} specializes in {specialty_text} in {location} and speaks {language_text}."


def _price_band(price: int) -> str:
    if price <= 0:
        return "Unknown"
    if price < 35000:
        return "<35000"
    if price < 50000:
        return "35000-50000"
    if price < 70000:
        return "50000-70000"
    return "70000+"


def _unique_rows(rows: tuple[dict[str, str], ...], *, key_name: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        key = row.get(key_name, "")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(dict(row))
    return unique
