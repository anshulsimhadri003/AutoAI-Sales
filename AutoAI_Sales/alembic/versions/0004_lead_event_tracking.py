"""add session-based lead event tracking

Revision ID: 0004_lead_event_tracking
Revises: 0003_live_deploy
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_lead_event_tracking"
down_revision = "0003_live_deploy"
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
    if not _has_table("user_events"):
        op.create_table(
            "user_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("dealership_id", sa.String(length=64), nullable=False),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("lead_public_id", sa.String(length=64), nullable=True),
            sa.Column("action", sa.String(length=32), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    for column in [
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("external_vehicle_id", sa.String(length=64), nullable=True),
        sa.Column("external_vehicle_name", sa.String(length=255), nullable=True),
        sa.Column("vin", sa.String(length=64), nullable=True),
        sa.Column("vehicle_year", sa.String(length=16), nullable=True),
        sa.Column("vehicle_make", sa.String(length=100), nullable=True),
        sa.Column("vehicle_model", sa.String(length=100), nullable=True),
    ]:
        _add_column_if_missing("leads", column)


def downgrade() -> None:
    pass
