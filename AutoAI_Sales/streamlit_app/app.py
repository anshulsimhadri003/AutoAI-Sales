from __future__ import annotations

import csv
import os
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import streamlit as st


DEFAULT_API_BASE_URL = os.getenv("DEFAULT_API_BASE_URL", "https://autosalesai.halcyontek.com")
DEFAULT_SITE_API_KEY = os.getenv("DEFAULT_SITE_API_KEY", "")
DEFAULT_DEALERSHIP_ID = "dealer-001"
DEFAULT_LEAD_FIRST_NAME = "Megan"
DEFAULT_LEAD_LAST_NAME = "Carter"
DEFAULT_LEAD_EMAIL = "megan.carter@example.com"
DEFAULT_LEAD_PHONE = "+1-555-0107"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@st.cache_data(show_spinner=False)
def load_seed_data() -> dict[str, list[dict[str, str]]]:
    def read_csv(filename: str) -> list[dict[str, str]]:
        path = DATA_DIR / filename
        with path.open(newline="", encoding="utf-8") as handle:
            return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]

    def unique_rows(rows: list[dict[str, str]], key_name: str) -> list[dict[str, str]]:
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for row in rows:
            key = row.get(key_name, "")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique

    return {
        "dealerships": unique_rows(read_csv("dealership_rules.csv"), "dealership_id"),
        "sales_reps": read_csv("sales_reps.csv"),
        "vehicles": read_csv("vehicles.csv"),
        "rep_availability": read_csv("rep_availability.csv"),
    }


def dealership_label(dealership: dict[str, str]) -> str:
    return f"{dealership['dealership_name']} ({dealership['dealership_id']})"


def vehicle_interest_text(vehicle: dict[str, str]) -> str:
    return " ".join(
        part
        for part in [vehicle.get("year", ""), vehicle.get("make", ""), vehicle.get("model", ""), vehicle.get("variant", "")]
        if part
    )


def vehicle_label(vehicle: dict[str, str]) -> str:
    status = vehicle.get("status", "unknown").replace("_", " ").title()
    return f"{vehicle['vehicle_id']} | {vehicle_interest_text(vehicle)} | {status} | {vehicle.get('location', 'Unknown')}"


def rep_label(rep: dict[str, str]) -> str:
    specialties = rep.get("vehicle_specialties", "").replace("|", ", ")
    return f"{rep['rep_id']} | {rep['rep_name']} | {rep.get('location', 'Unknown')} | {specialties}"


def dealership_vehicles(rows: list[dict[str, str]], dealership_id: str) -> list[dict[str, str]]:
    def sort_key(vehicle: dict[str, str]) -> tuple[int, int, str]:
        unavailable = 0 if vehicle.get("status") == "available" and vehicle.get("available_for_test_drive") == "true" else 1
        return (unavailable, -int(vehicle.get("year") or 0), vehicle.get("vehicle_id", ""))

    return sorted([row for row in rows if row.get("dealership_id") == dealership_id], key=sort_key)


def dealership_reps(rows: list[dict[str, str]], dealership_id: str) -> list[dict[str, str]]:
    return sorted([row for row in rows if row.get("dealership_id") == dealership_id], key=lambda rep: rep.get("rep_name", ""))


def available_dates(rows: list[dict[str, str]], dealership_id: str) -> list[date]:
    dates = sorted(
        {
            row["date"]
            for row in rows
            if row.get("dealership_id") == dealership_id and row.get("status", "").lower() == "available"
        }
    )
    return [date.fromisoformat(value) for value in dates]


def default_time_window(
    rows: list[dict[str, str]],
    dealership_id: str,
    rep_id: str | None,
    target_date: date,
    duration_minutes: int,
) -> tuple[str, str]:
    target = target_date.isoformat()
    matching_rows = [
        row
        for row in rows
        if row.get("dealership_id") == dealership_id
        and row.get("date") == target
        and row.get("status", "").lower() == "available"
        and (not rep_id or row.get("rep_id") == rep_id)
    ]
    if matching_rows:
        start_time = matching_rows[0].get("start_time", "10:00")
        start = f"{target}T{start_time}:00"
        start_dt = pd.Timestamp(start)
        end_dt = start_dt + pd.Timedelta(minutes=duration_minutes)
        return start_dt.isoformat(), end_dt.isoformat()
    return f"{target}T11:00:00", f"{target}T12:00:00"


def api_request(
    method: str,
    base_url: str,
    path: str,
    dealership_id: str | None = None,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    site_api_key: str | None = None,
) -> tuple[int | None, Any]:
    headers: dict[str, str] = {"X-Request-ID": str(uuid.uuid4())}
    if dealership_id:
        headers["X-Dealership-ID"] = dealership_id
    if site_api_key:
        headers["X-API-Key"] = site_api_key

    url = f"{base_url.rstrip('/')}" + path

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.request(method, url, headers=headers, json=json_body, params=params)
    except httpx.RequestError as exc:
        return None, f"Request failed: {exc}"

    try:
        payload = response.json()
    except ValueError:
        payload = response.text

    return response.status_code, payload


def show_api_result(status_code: int | None, payload: Any, *, success_message: str) -> bool:
    if status_code is None:
        st.error(payload)
        return False

    if 200 <= status_code < 300:
        st.success(f"{success_message} ({status_code})")
        if isinstance(payload, (dict, list)):
            st.json(payload)
        else:
            st.code(str(payload))
        return True

    st.error(f"API returned {status_code}")
    if isinstance(payload, (dict, list)):
        st.json(payload)
    else:
        payload_text = str(payload)
        if "<html" in payload_text.lower():
            st.warning("The response looks like HTML, which usually means the request hit the Streamlit site or proxy instead of FastAPI.")
        st.code(payload_text)
    return False


def init_state() -> None:
    st.session_state.setdefault("latest_lead", None)
    st.session_state.setdefault("lead_rows", [])
    st.session_state.setdefault("appointment_rows", [])
    st.session_state.setdefault("slot_rows", [])
    st.session_state.setdefault("dashboard_bundle", None)


def lead_label(lead: dict[str, Any]) -> str:
    return (
        f"{lead['public_id']} | {lead['first_name']} {lead['last_name']} | "
        f"{lead['temperature']} | score {lead['score']}"
    )


st.set_page_config(page_title="Halcyon Auto Sales API Playground", layout="wide")
init_state()
seed_data = load_seed_data()

st.title("Halcyon Auto Sales API Playground")
st.caption("Use this Streamlit app to exercise lead intent scoring, persisted signals, AI reply generation, and appointment flows.")

with st.sidebar:
    st.header("Connection")
    api_base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)
    site_api_key = st.text_input("Site API Key (optional)", value=DEFAULT_SITE_API_KEY, type="password")
    dealership_rows = seed_data["dealerships"]
    dealership_options = [dealership_label(row) for row in dealership_rows]
    default_dealership_index = next(
        (index for index, row in enumerate(dealership_rows) if row.get("dealership_id") == DEFAULT_DEALERSHIP_ID),
        0,
    )
    selected_dealership_label = st.selectbox("Dealership", options=dealership_options, index=default_dealership_index)
    selected_dealership = dealership_rows[dealership_options.index(selected_dealership_label)]
    dealership_id = selected_dealership["dealership_id"]
    st.caption("Use the same public domain for Streamlit UI and FastAPI only when the reverse proxy routes /api and /health to FastAPI.")
    st.caption(
        f"Using CSV seed data for {selected_dealership['dealership_name']} in {selected_dealership['timezone']}."
    )

    dealership_vehicle_rows = dealership_vehicles(seed_data["vehicles"], dealership_id)
    dealership_rep_rows = dealership_reps(seed_data["sales_reps"], dealership_id)
    dealership_dates = available_dates(seed_data["rep_availability"], dealership_id)
    primary_vehicle = dealership_vehicle_rows[0] if dealership_vehicle_rows else None
    primary_rep = dealership_rep_rows[0] if dealership_rep_rows else None
    default_slot_date = dealership_dates[0] if dealership_dates else date.today() + timedelta(days=1)
    default_duration_minutes = int(selected_dealership.get("default_test_drive_duration_mins") or 60)
    primary_location = (
        (primary_vehicle or {}).get("location")
        or (primary_rep or {}).get("location")
        or "Austin, TX"
    )

    with st.expander("Seed Snapshot", expanded=True):
        st.write(f"Dealership ID: `{dealership_id}`")
        st.write(f"Inventory loaded: `{len(dealership_vehicle_rows)}` vehicles")
        st.write(f"Sales reps loaded: `{len(dealership_rep_rows)}` reps")
        st.write(f"Default slot date: `{default_slot_date.isoformat()}`")

    if st.button("Check Health", use_container_width=True):
        status_code, payload = api_request("GET", api_base_url, "/health", site_api_key=site_api_key)
        show_api_result(status_code, payload, success_message="API health check passed")

vehicle_options = [vehicle_label(vehicle) for vehicle in dealership_vehicle_rows]
vehicle_lookup = {vehicle_label(vehicle): vehicle for vehicle in dealership_vehicle_rows}
rep_options = [rep_label(rep) for rep in dealership_rep_rows]
rep_lookup = {rep_label(rep): rep for rep in dealership_rep_rows}
default_vehicle_label = vehicle_options[0] if vehicle_options else ""
default_rep_label = rep_options[0] if rep_options else ""
default_vehicle_interest = vehicle_interest_text(primary_vehicle) if primary_vehicle else "Ford F-150 XLT"
default_lead_message = (
    f"I'm interested in the {default_vehicle_interest} at {selected_dealership['dealership_name']}. "
    "I'd like to schedule a test drive this week and compare finance options."
)
default_reply_message = "What can you do?"
fallback_start_time, fallback_end_time = default_time_window(
    seed_data["rep_availability"],
    dealership_id,
    primary_rep.get("rep_id") if primary_rep else None,
    default_slot_date,
    default_duration_minutes,
)

lead_tab, browse_tab, reply_tab, appointments_tab, dashboard_tab = st.tabs(
    ["Lead Intent Tester", "Lead Explorer", "AI Reply", "Appointments", "Dashboard"]
)

with lead_tab:
    st.subheader("Create Lead")
    st.write("Create a lead with explicit intent signals or fall back to message-derived signals only.")

    with st.form("create_lead_form"):
        col1, col2 = st.columns(2)
        with col1:
            source_channel = st.selectbox(
                "Source Channel",
                options=["website_form", "chat_widget", "whatsapp", "email", "phone_call"],
                index=0,
            )
            first_name = st.text_input("First Name", value=DEFAULT_LEAD_FIRST_NAME)
            last_name = st.text_input("Last Name", value=DEFAULT_LEAD_LAST_NAME)
            email = st.text_input("Email", value=DEFAULT_LEAD_EMAIL)
            phone = st.text_input("Phone", value=DEFAULT_LEAD_PHONE)
            if vehicle_options:
                selected_vehicle_label = st.selectbox("Vehicle Interest", options=vehicle_options, index=0)
                selected_vehicle = vehicle_lookup[selected_vehicle_label]
                vehicle_interest = vehicle_interest_text(selected_vehicle)
            else:
                vehicle_interest = st.text_input("Vehicle Interest", value=default_vehicle_interest)
            customer_location = st.text_input("Customer Location", value=primary_location)
        with col2:
            message = st.text_area(
                "Lead Message",
                value=default_lead_message,
                height=140,
            )
            include_intent_signals = st.checkbox("Include explicit intent_signals", value=True)
            test_drive_interest = st.checkbox("Test Drive Interest", value=True)

        st.markdown("### Intent Signals")
        sig1, sig2, sig3 = st.columns(3)
        with sig1:
            page_views = st.slider("Page Views", min_value=0, max_value=25, value=8)
            chat_interactions = st.slider("Chat Interactions", min_value=0, max_value=10, value=3)
        with sig2:
            vehicle_page_time_seconds = st.slider(
                "Vehicle Page Time (seconds)",
                min_value=0,
                max_value=900,
                step=30,
                value=480,
            )
            financing_inquiries = st.slider("Financing Inquiries", min_value=0, max_value=5, value=1)
        with sig3:
            trade_in_requests = st.slider("Trade-In Requests", min_value=0, max_value=3, value=1)

        submitted = st.form_submit_button("Create Lead", use_container_width=True)

    if submitted:
        payload: dict[str, Any] = {
            "source_channel": source_channel,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "vehicle_interest": vehicle_interest,
            "message": message,
            "customer_location": customer_location,
        }

        if include_intent_signals:
            payload["intent_signals"] = {
                "page_views": page_views,
                "vehicle_page_time_seconds": vehicle_page_time_seconds,
                "chat_interactions": chat_interactions,
                "financing_inquiries": financing_inquiries,
                "trade_in_requests": trade_in_requests,
                "test_drive_interest": test_drive_interest,
            }

        status_code, response_payload = api_request(
            "POST",
            api_base_url,
            "/api/v1/leads",
            dealership_id,
            json_body=payload,
            site_api_key=site_api_key,
        )
        if show_api_result(status_code, response_payload, success_message="Lead created"):
            st.session_state["latest_lead"] = response_payload

            metric1, metric2, metric3 = st.columns(3)
            metric1.metric("Lead Score", response_payload["score"])
            metric2.metric("Temperature", response_payload["temperature"])
            metric3.metric("Urgency", response_payload["urgency"])

    latest_lead = st.session_state.get("latest_lead")
    if latest_lead:
        st.markdown("### Last Created Lead")
        highlight1, highlight2, highlight3 = st.columns(3)
        highlight1.metric("Lead ID", latest_lead["public_id"])
        highlight2.metric("Assigned Rep", latest_lead["assigned_rep"])
        highlight3.metric("Next Action", latest_lead["next_action"])

with browse_tab:
    st.subheader("Browse Leads")
    if st.button("Refresh Leads", use_container_width=True):
        status_code, response_payload = api_request("GET", api_base_url, "/api/v1/leads", dealership_id, site_api_key=site_api_key)
        if show_api_result(status_code, response_payload, success_message="Fetched leads"):
            st.session_state["lead_rows"] = response_payload

    lead_rows = st.session_state.get("lead_rows", [])
    if lead_rows:
        summary_rows = [
            {
                "public_id": lead["public_id"],
                "name": f"{lead['first_name']} {lead['last_name']}",
                "vehicle_interest": lead["vehicle_interest"],
                "score": lead["score"],
                "temperature": lead["temperature"],
                "page_views": lead["intent_signals"]["page_views"],
                "chat_interactions": lead["intent_signals"]["chat_interactions"],
                "test_drive_interest": lead["intent_signals"]["test_drive_interest"],
            }
            for lead in lead_rows
        ]
        st.dataframe(summary_rows, use_container_width=True, hide_index=True)

        default_index = 0
        latest_public_id = st.session_state.get("latest_lead", {}).get("public_id") if st.session_state.get("latest_lead") else None
        if latest_public_id:
            for idx, row in enumerate(lead_rows):
                if row["public_id"] == latest_public_id:
                    default_index = idx
                    break

        selected_label = st.selectbox(
            "Inspect Lead",
            options=[lead_label(lead) for lead in lead_rows],
            index=default_index,
        )
        selected_lead = lead_rows[[lead_label(lead) for lead in lead_rows].index(selected_label)]

        st.markdown("### Lead Detail")
        left, right = st.columns(2)
        with left:
            st.metric("Score", selected_lead["score"])
            st.metric("Temperature", selected_lead["temperature"])
            st.metric("Urgency", selected_lead["urgency"])
        with right:
            st.metric("Assigned Rep", selected_lead["assigned_rep"])
            st.metric("Status", selected_lead["status"])
            st.metric("Next Action", selected_lead["next_action"])

        st.markdown("### Persisted Intent Signals")
        st.json(selected_lead["intent_signals"])

        if st.button("Fetch Selected Lead From API", use_container_width=True):
            status_code, response_payload = api_request(
                "GET",
                api_base_url,
                f"/api/v1/leads/{selected_lead['public_id']}",
                dealership_id,
                site_api_key=site_api_key,
            )
            show_api_result(status_code, response_payload, success_message="Fetched lead detail")
    else:
        st.info("No leads loaded yet. Click 'Refresh Leads' to pull data from the API.")

with reply_tab:
    st.subheader("Generate AI Reply")

    latest_lead_id = ""
    if st.session_state.get("latest_lead"):
        latest_lead_id = st.session_state["latest_lead"]["public_id"]

    with st.form("reply_form"):
        use_lead_context = st.checkbox("Use latest lead context", value=False)

        reply_lead_id = st.text_input(
            "Lead ID (optional)",
            value=latest_lead_id if use_lead_context else ""
        )

        reply_message = st.text_area(
            "Customer Message",
            value="What can you do?",
            height=120,
        )

        reply_submitted = st.form_submit_button("Generate Reply", use_container_width=True)

    if reply_submitted:
        payload = {"message": reply_message.strip()}

        if use_lead_context and reply_lead_id.strip():
            payload["lead_id"] = reply_lead_id.strip()

        st.caption("Payload being sent")
        st.json(payload)

        status_code, response_payload = api_request(
            "POST",
            api_base_url,
            "/api/v1/messages/reply",
            dealership_id,
            json_body=payload,
            site_api_key=site_api_key,
        )

        if show_api_result(status_code, response_payload, success_message="Generated AI reply"):
            st.markdown("### Reply")
            st.write(response_payload.get("reply", "No reply returned"))

with appointments_tab:
    st.subheader("Appointments")
    slot_col, book_col = st.columns(2)

    with slot_col:
        st.markdown("### Get Available Slots")
        with st.form("slots_form"):
            if vehicle_options:
                selected_slot_vehicle_label = st.selectbox("Vehicle", options=vehicle_options, index=0, key="slot_vehicle")
                slot_vehicle_id = vehicle_lookup[selected_slot_vehicle_label]["vehicle_id"]
            else:
                slot_vehicle_id = st.text_input("Vehicle ID", value="VH-001")
            slot_date = st.date_input("Date", value=default_slot_date)
            slots_submitted = st.form_submit_button("Fetch Slots", use_container_width=True)

        if slots_submitted:
            status_code, response_payload = api_request(
                "GET",
                api_base_url,
                "/api/v1/appointments/slots",
                dealership_id,
                params={"vehicle_id": slot_vehicle_id, "date": slot_date.isoformat()},
                site_api_key=site_api_key,
            )
            if show_api_result(status_code, response_payload, success_message="Fetched appointment slots"):
                st.session_state["slot_rows"] = response_payload

        slot_rows = st.session_state.get("slot_rows", [])
        slot_options = [f"{slot['start']} -> {slot['end']}" for slot in slot_rows]
        selected_slot = st.selectbox(
            "Available Slots",
            options=slot_options if slot_options else ["No slots loaded yet"],
            index=0,
        )

    with book_col:
        st.markdown("### Book Appointment")
        latest_lead_id = ""
        if st.session_state.get("latest_lead"):
            latest_lead_id = st.session_state["latest_lead"]["public_id"]

        with st.form("book_appointment_form"):
            appointment_lead_id = st.text_input("Lead ID", value=latest_lead_id)
            if vehicle_options:
                selected_book_vehicle_label = st.selectbox(
                    "Vehicle",
                    options=vehicle_options,
                    index=0,
                    key="book_vehicle",
                )
                appointment_vehicle_id = vehicle_lookup[selected_book_vehicle_label]["vehicle_id"]
            else:
                appointment_vehicle_id = st.text_input("Vehicle ID", value="VH-001")
            if rep_options:
                selected_rep_label = st.selectbox("Sales Rep", options=rep_options, index=0, key="book_rep")
                rep_id = rep_lookup[selected_rep_label]["rep_id"]
            else:
                rep_id = st.text_input("Rep ID", value="REP-001")
            channel = st.selectbox("Channel", options=["showroom", "whatsapp", "phone", "email"], index=0)

            if slot_rows:
                default_start = slot_rows[0]["start"]
                default_end = slot_rows[0]["end"]
            else:
                default_start = fallback_start_time
                default_end = fallback_end_time

            start_time = st.text_input("Start Time", value=default_start)
            end_time = st.text_input("End Time", value=default_end)
            book_submitted = st.form_submit_button("Book Appointment", use_container_width=True)

        if book_submitted:
            payload = {
                "lead_id": appointment_lead_id,
                "vehicle_id": appointment_vehicle_id,
                "rep_id": rep_id,
                "start_time": start_time,
                "end_time": end_time,
                "channel": channel,
            }
            status_code, response_payload = api_request(
                "POST",
                api_base_url,
                "/api/v1/appointments/book",
                dealership_id,
                json_body=payload,
                site_api_key=site_api_key,
            )
            if show_api_result(status_code, response_payload, success_message="Appointment booked"):
                st.session_state["appointment_rows"] = [response_payload] + st.session_state.get("appointment_rows", [])

    st.markdown("### Existing Appointments")
    if st.button("Refresh Appointments", use_container_width=True):
        status_code, response_payload = api_request("GET", api_base_url, "/api/v1/appointments", dealership_id, site_api_key=site_api_key)
        if show_api_result(status_code, response_payload, success_message="Fetched appointments"):
            st.session_state["appointment_rows"] = response_payload

    appointment_rows = st.session_state.get("appointment_rows", [])
    if appointment_rows:
        st.dataframe(appointment_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No appointments loaded yet. Fetch them from the API or book a new one.")

with dashboard_tab:
    st.subheader("Lead Metrics and Intent Trends")
    st.write("Blend the API dashboard endpoints with live lead data to inspect score trends and engagement quality.")

    if st.button("Refresh Dashboard", use_container_width=True):
        lead_metrics_status, lead_metrics_payload = api_request(
            "GET",
            api_base_url,
            "/api/v1/dashboard/lead-metrics",
            dealership_id,
            site_api_key=site_api_key,
        )
        sequence_status, sequence_payload = api_request(
            "GET",
            api_base_url,
            "/api/v1/dashboard/sequence-metrics",
            dealership_id,
            site_api_key=site_api_key,
        )
        appointment_status, appointment_payload = api_request(
            "GET",
            api_base_url,
            "/api/v1/dashboard/appointment-metrics",
            dealership_id,
            site_api_key=site_api_key,
        )
        leads_status, leads_payload = api_request(
            "GET",
            api_base_url,
            "/api/v1/leads",
            dealership_id,
            site_api_key=site_api_key,
        )

        if all(code is not None and 200 <= code < 300 for code in [lead_metrics_status, sequence_status, appointment_status, leads_status]):
            st.session_state["dashboard_bundle"] = {
                "lead_metrics": lead_metrics_payload,
                "sequence_metrics": sequence_payload,
                "appointment_metrics": appointment_payload,
                "leads": leads_payload,
            }
            st.success("Dashboard data refreshed")
        else:
            st.error("One or more dashboard requests failed")
            for label, code, payload in [
                ("lead_metrics", lead_metrics_status, lead_metrics_payload),
                ("sequence_metrics", sequence_status, sequence_payload),
                ("appointment_metrics", appointment_status, appointment_payload),
                ("leads", leads_status, leads_payload),
            ]:
                with st.expander(f"{label} response"):
                    if code is None:
                        st.error(payload)
                    else:
                        st.write(f"Status: {code}")
                        if isinstance(payload, (dict, list)):
                            st.json(payload)
                        else:
                            st.code(str(payload))

    dashboard_bundle = st.session_state.get("dashboard_bundle")
    if dashboard_bundle:
        lead_metrics = dashboard_bundle["lead_metrics"]
        sequence_metrics = dashboard_bundle["sequence_metrics"]
        appointment_metrics = dashboard_bundle["appointment_metrics"]
        lead_rows = dashboard_bundle["leads"]

        top1, top2, top3, top4 = st.columns(4)
        top1.metric("Leads Processed", lead_metrics["leads_processed"])
        top2.metric("Hot Leads", lead_metrics["hot_leads"])
        top3.metric("Active Conversations", lead_metrics["active_conversations"])
        top4.metric("Avg Response Time", lead_metrics["avg_response_time"])

        if lead_rows:
            leads_df = pd.DataFrame(lead_rows)
            signals_df = pd.json_normalize(leads_df["intent_signals"])
            leads_df = pd.concat([leads_df.drop(columns=["intent_signals"]), signals_df], axis=1)
            leads_df["created_at"] = pd.to_datetime(leads_df["created_at"], errors="coerce")
            leads_df["created_day"] = leads_df["created_at"].dt.date

            avg_score = round(float(leads_df["score"].mean()), 1)
            high_intent = int((leads_df["score"] >= 80).sum())
            finance_engaged = int((leads_df["financing_inquiries"] > 0).sum())
            trade_in_engaged = int((leads_df["trade_in_requests"] > 0).sum())

            summary1, summary2, summary3, summary4 = st.columns(4)
            summary1.metric("Average Intent Score", avg_score)
            summary2.metric("High-Intent Leads", high_intent)
            summary3.metric("Finance Engaged", finance_engaged)
            summary4.metric("Trade-In Engaged", trade_in_engaged)

            trend_df = (
                leads_df.sort_values("created_at")
                .groupby("created_day", dropna=False)
                .agg(
                    avg_score=("score", "mean"),
                    lead_count=("public_id", "count"),
                    chat_interactions=("chat_interactions", "sum"),
                )
                .reset_index()
            )

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("### Intent Score Trend")
                st.line_chart(trend_df.set_index("created_day")["avg_score"])
            with chart_col2:
                st.markdown("### Lead Volume Trend")
                st.bar_chart(trend_df.set_index("created_day")["lead_count"])

            lower_col, right_col = st.columns(2)
            with lower_col:
                st.markdown("### Temperature Mix")
                temperature_counts = leads_df["temperature"].value_counts()
                st.bar_chart(temperature_counts)
            with right_col:
                st.markdown("### Sequence and Appointment Snapshot")
                snapshot_rows = [
                    {"metric": "Active Sequences", "value": sequence_metrics["active_sequences"]},
                    {"metric": "Engagement Rate", "value": sequence_metrics["engagement_rate"]},
                    {"metric": "Response Rate", "value": sequence_metrics["response_rate"]},
                    {"metric": "Escalations", "value": sequence_metrics["escalations"]},
                    {"metric": "Appointments Scheduled", "value": appointment_metrics["appointments_scheduled"]},
                    {"metric": "Show Rate", "value": appointment_metrics["show_rate"]},
                    {"metric": "No-Show Rate", "value": appointment_metrics["no_show_rate"]},
                    {"metric": "Reschedules", "value": appointment_metrics["reschedules"]},
                ]
                st.dataframe(snapshot_rows, use_container_width=True, hide_index=True)

            st.markdown("### Top Intent Leads")
            top_leads = leads_df.sort_values(["score", "created_at"], ascending=[False, False]).head(10)
            st.dataframe(
                top_leads[
                    [
                        "public_id",
                        "first_name",
                        "last_name",
                        "vehicle_interest",
                        "score",
                        "temperature",
                        "page_views",
                        "vehicle_page_time_seconds",
                        "chat_interactions",
                        "financing_inquiries",
                        "trade_in_requests",
                        "test_drive_interest",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No leads returned yet, so trend charts are waiting for data.")
    else:
        st.info("Click 'Refresh Dashboard' to load dashboard metrics and intent-score trends.")
