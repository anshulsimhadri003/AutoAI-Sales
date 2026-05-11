"""expand schema for live deploy

Revision ID: 0003_live_deploy
Revises: 0002_lead_intent_cols
Create Date: 2026-04-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_live_deploy"
down_revision = "0002_lead_intent_cols"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)} if inspector.has_table(table_name) else set()


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    if not _has_table("sales_reps"):
        op.create_table(
            "sales_reps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=50), nullable=False),
            sa.Column("location", sa.String(length=100), nullable=False),
            sa.Column("specializations", sa.JSON(), nullable=False),
            sa.Column("languages", sa.JSON(), nullable=False),
            sa.Column("profile_text", sa.Text(), nullable=False),
            sa.Column("workload", sa.Integer(), nullable=False),
            sa.Column("max_active_leads", sa.Integer(), nullable=False),
            sa.Column("is_available", sa.Boolean(), nullable=False),
            sa.Column("manager_email", sa.String(length=255), nullable=True),
            sa.Column("calendar_key", sa.String(length=255), nullable=True),
            sa.Column("available_start_hour", sa.Integer(), nullable=False),
            sa.Column("available_end_hour", sa.Integer(), nullable=False),
        )

    if not _has_table("vehicle_inventory"):
        op.create_table(
            "vehicle_inventory",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("stock_no", sa.String(length=64), nullable=True),
            sa.Column("make_model", sa.String(length=255), nullable=False),
            sa.Column("trim", sa.String(length=255), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("body_type", sa.String(length=100), nullable=False),
            sa.Column("fuel_type", sa.String(length=50), nullable=False),
            sa.Column("transmission", sa.String(length=50), nullable=False),
            sa.Column("price", sa.Integer(), nullable=False),
            sa.Column("price_band", sa.String(length=100), nullable=False),
            sa.Column("color", sa.String(length=50), nullable=False),
            sa.Column("location", sa.String(length=100), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("available_for_test_drive", sa.Boolean(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
        )

    if not _has_table("message_events"):
        op.create_table(
            "message_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("sequence_public_id", sa.String(length=64), nullable=True),
            sa.Column("lead_public_id", sa.String(length=64), nullable=True),
            sa.Column("channel", sa.String(length=50), nullable=False),
            sa.Column("direction", sa.String(length=20), nullable=False),
            sa.Column("template_key", sa.String(length=100), nullable=True),
            sa.Column("classification", sa.String(length=100), nullable=True),
            sa.Column("delivery_status", sa.String(length=50), nullable=False),
            sa.Column("opened_at", sa.DateTime(), nullable=True),
            sa.Column("clicked_at", sa.DateTime(), nullable=True),
            sa.Column("replied_at", sa.DateTime(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("appointment_reminders"):
        op.create_table(
            "appointment_reminders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("appointment_public_id", sa.String(length=64), nullable=False),
            sa.Column("reminder_type", sa.String(length=32), nullable=False),
            sa.Column("channel", sa.String(length=32), nullable=False),
            sa.Column("due_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
        )

    if not _has_table("dealership_rules"):
        op.create_table(
            "dealership_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("response_sla_minutes", sa.Integer(), nullable=False),
            sa.Column("max_leads_per_rep", sa.Integer(), nullable=False),
            sa.Column("allow_after_hours_booking", sa.Boolean(), nullable=False),
            sa.Column("default_test_drive_duration_mins", sa.Integer(), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False),
        )

    if not _has_table("store_hours"):
        op.create_table(
            "store_hours",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("day_of_week", sa.String(length=16), nullable=False),
            sa.Column("open_time", sa.String(length=8), nullable=False),
            sa.Column("close_time", sa.String(length=8), nullable=False),
            sa.Column("is_open", sa.Boolean(), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False),
        )

    if not _has_table("rep_availability"):
        op.create_table(
            "rep_availability",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rep_id", sa.String(length=64), nullable=False),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("date", sa.String(length=16), nullable=False),
            sa.Column("start_time", sa.String(length=8), nullable=False),
            sa.Column("end_time", sa.String(length=8), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
        )

    if not _has_table("sequence_definitions"):
        op.create_table(
            "sequence_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("channel", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("trigger_type", sa.String(length=64), nullable=False),
        )

    if not _has_table("sequence_step_definitions"):
        op.create_table(
            "sequence_step_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("sequence_public_id", sa.String(length=64), nullable=False),
            sa.Column("step_order", sa.Integer(), nullable=False),
            sa.Column("delay_minutes", sa.Integer(), nullable=False),
            sa.Column("template_id", sa.String(length=64), nullable=False),
            sa.Column("condition_type", sa.String(length=64), nullable=False),
            sa.Column("condition_value", sa.String(length=255), nullable=True),
        )

    lead_additions = [
        sa.Column("crm_id", sa.String(length=64), nullable=True),
        sa.Column("customer_location", sa.String(length=100), nullable=False, server_default="Unknown"),
        sa.Column("budget_indicator", sa.String(length=100), nullable=False, server_default="Unknown"),
        sa.Column("engagement_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("previous_dealership_interactions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("semantic_intent", sa.String(length=100), nullable=False, server_default="general_interest"),
        sa.Column("semantic_intent_similarity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("assigned_rep_id", sa.String(length=64), nullable=True),
        sa.Column("dedup_status", sa.String(length=50), nullable=False, server_default="unique"),
        sa.Column("merged_into_public_id", sa.String(length=64), nullable=True),
        sa.Column("merged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_response_at", sa.DateTime(), nullable=True),
        sa.Column("last_customer_message_at", sa.DateTime(), nullable=True),
        sa.Column("last_agent_message_at", sa.DateTime(), nullable=True),
        sa.Column("sla_due_at", sa.DateTime(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    ]
    for column in lead_additions:
        _add_column_if_missing("leads", column)

    sequence_additions = [
        sa.Column("definition_public_id", sa.String(length=64), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("current_template_id", sa.String(length=64), nullable=True),
        sa.Column("paused_reason", sa.String(length=255), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("conversion_outcome", sa.String(length=100), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_message_classification", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    ]
    for column in sequence_additions:
        _add_column_if_missing("sequences", column)

    appointment_additions = [
        sa.Column("vehicle_location", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("vehicle_status", sa.String(length=50), nullable=False, server_default="available"),
        sa.Column("attendance_status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("rescheduled_from_public_id", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    ]
    for column in appointment_additions:
        _add_column_if_missing("appointments", column)


def downgrade() -> None:
    pass
