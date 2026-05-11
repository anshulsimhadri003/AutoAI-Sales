from __future__ import annotations

from typing import Any, TypedDict


class LeadIntakeState(TypedDict, total=False):
    dealership_id: str
    payload: Any
    qualification: dict[str, Any]
    duplicate_found: bool
    assigned_rep: Any
    lead: Any


class ReplyState(TypedDict, total=False):
    dealership_id: str
    payload: Any
    context: dict[str, Any]
    classification: dict[str, Any]
    retrieval: dict[str, Any]
    reply: str
    response: Any


class AppointmentState(TypedDict, total=False):
    dealership_id: str
    payload: Any
    appointment: Any
    validation: dict[str, Any]
    background_tasks: Any
