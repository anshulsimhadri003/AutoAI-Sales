from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from shared.models.models import DealershipRule, RepAvailability, SalesRep, StoreHour
from shared.repositories.appointment_repository import AppointmentRepository


class CalendarClient:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AppointmentRepository(db)

    def get_available_slots(self, dealership_id: str, vehicle_id: str, date: str, rep_id: str | None = None):
        del vehicle_id
        reps = self._get_candidate_reps(dealership_id, rep_id)
        if not reps:
            return []

        for rep in reps:
            slots = self._slots_for_rep(dealership_id, rep, date)
            if slots:
                return slots[:10]
        return []

    def is_slot_available(
        self,
        dealership_id: str,
        vehicle_id: str,
        rep_id: str,
        start_time: str,
        end_time: str,
    ) -> bool:
        del vehicle_id
        requested_start = datetime.fromisoformat(start_time)
        requested_end = datetime.fromisoformat(end_time)
        for slot in self.get_available_slots(dealership_id, "", requested_start.date().isoformat(), rep_id=rep_id):
            slot_start = datetime.fromisoformat(slot["start"])
            slot_end = datetime.fromisoformat(slot["end"])
            if slot_start == requested_start and slot_end == requested_end:
                return True
        return False

    def create_event(self, dealership_id: str, appointment) -> None:
        del dealership_id, appointment
        return None

    def _get_candidate_reps(self, dealership_id: str, rep_id: str | None) -> list[SalesRep]:
        if rep_id:
            rep = (
                self.db.query(SalesRep)
                .filter(SalesRep.dealership_id == dealership_id, SalesRep.public_id == rep_id)
                .first()
            )
            return [rep] if rep else []

        return (
            self.db.query(SalesRep)
            .filter(SalesRep.dealership_id == dealership_id, SalesRep.is_available.is_(True))
            .order_by(SalesRep.workload.asc(), SalesRep.name.asc())
            .all()
        )

    def _slots_for_rep(self, dealership_id: str, rep: SalesRep, date: str) -> list[dict[str, str]]:
        rule = self._get_rule(dealership_id)
        store_window = self._store_window(dealership_id, date)
        if not store_window and not (rule and rule.allow_after_hours_booking):
            return []

        base_windows = self._rep_windows(dealership_id, rep, date, store_window, rule)
        if not base_windows:
            return []

        duration_minutes = self._slot_duration_minutes(rule)
        blocked_windows = self._blocked_windows(dealership_id, rep.public_id, date)
        slots: list[dict[str, str]] = []
        for start_window, end_window in base_windows:
            current = start_window
            while current + timedelta(minutes=duration_minutes) <= end_window:
                slot_end = current + timedelta(minutes=duration_minutes)
                if not self._overlaps_any(current, slot_end, blocked_windows):
                    slots.append({"start": current.isoformat(), "end": slot_end.isoformat()})
                current += timedelta(minutes=30)
        slots.sort(key=lambda item: item["start"])
        return slots

    def _rep_windows(
        self,
        dealership_id: str,
        rep: SalesRep,
        date: str,
        store_window: tuple[datetime, datetime] | None,
        rule: DealershipRule | None,
    ) -> list[tuple[datetime, datetime]]:
        allow_after_hours = rule.allow_after_hours_booking if rule else False
        availability_rows = (
            self.db.query(RepAvailability)
            .filter(
                RepAvailability.dealership_id == dealership_id,
                RepAvailability.rep_id == rep.public_id,
                RepAvailability.date == date,
            )
            .order_by(RepAvailability.start_time.asc())
            .all()
        )

        available_windows = [
            (self._combine(date, row.start_time), self._combine(date, row.end_time))
            for row in availability_rows
            if row.status.lower() == "available"
        ]
        if not available_windows:
            available_windows = [
                (
                    self._combine(date, f"{rep.available_start_hour:02d}:00"),
                    self._combine(date, f"{rep.available_end_hour:02d}:00"),
                )
            ]

        if store_window and not allow_after_hours:
            available_windows = [
                window
                for base_window in available_windows
                if (window := self._intersect_window(base_window, store_window)) is not None
            ]

        blocked_from_availability = [
            (self._combine(date, row.start_time), self._combine(date, row.end_time))
            for row in availability_rows
            if row.status.lower() in {"busy", "blocked"}
        ]

        windows: list[tuple[datetime, datetime]] = []
        for start_window, end_window in available_windows:
            current_start = start_window
            for blocked_start, blocked_end in sorted(blocked_from_availability):
                if blocked_end <= current_start or blocked_start >= end_window:
                    continue
                if blocked_start > current_start:
                    windows.append((current_start, blocked_start))
                current_start = max(current_start, blocked_end)
            if current_start < end_window:
                windows.append((current_start, end_window))
        return [(start, end) for start, end in windows if start < end]

    def _blocked_windows(self, dealership_id: str, rep_id: str, date: str) -> list[tuple[datetime, datetime]]:
        existing = self.repo.list_by_rep_and_date(dealership_id, rep_id, date)
        return [
            (datetime.fromisoformat(item.start_time), datetime.fromisoformat(item.end_time))
            for item in existing
        ]

    def _store_window(self, dealership_id: str, date: str) -> tuple[datetime, datetime] | None:
        day_name = datetime.fromisoformat(date).strftime("%A")
        row = (
            self.db.query(StoreHour)
            .filter(StoreHour.dealership_id == dealership_id, StoreHour.day_of_week == day_name)
            .first()
        )
        if row is None or not row.is_open:
            return None
        return self._combine(date, row.open_time), self._combine(date, row.close_time)

    def _get_rule(self, dealership_id: str) -> DealershipRule | None:
        return self.db.query(DealershipRule).filter(DealershipRule.dealership_id == dealership_id).first()

    def _slot_duration_minutes(self, rule: DealershipRule | None) -> int:
        return rule.default_test_drive_duration_mins if rule else 30

    def _combine(self, date: str, time_text: str) -> datetime:
        normalized = time_text if len(time_text) > 5 else f"{time_text}:00"
        return datetime.fromisoformat(f"{date}T{normalized}")

    def _intersect_window(
        self,
        first: tuple[datetime, datetime],
        second: tuple[datetime, datetime],
    ) -> tuple[datetime, datetime] | None:
        start = max(first[0], second[0])
        end = min(first[1], second[1])
        if start >= end:
            return None
        return start, end

    def _overlaps_any(
        self,
        start: datetime,
        end: datetime,
        blocked_windows: list[tuple[datetime, datetime]],
    ) -> bool:
        return any(start < blocked_end and end > blocked_start for blocked_start, blocked_end in blocked_windows)
