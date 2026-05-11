"""add lead intent signal columns

Revision ID: 0002_lead_intent_cols
Revises: 0001_initial_schema
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_lead_intent_cols"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("page_views", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "leads",
        sa.Column("vehicle_page_time_seconds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("leads", sa.Column("chat_interactions", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("leads", sa.Column("financing_inquiries", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("leads", sa.Column("trade_in_requests", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "leads",
        sa.Column("test_drive_interest", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("leads", "test_drive_interest")
    op.drop_column("leads", "trade_in_requests")
    op.drop_column("leads", "financing_inquiries")
    op.drop_column("leads", "chat_interactions")
    op.drop_column("leads", "vehicle_page_time_seconds")
    op.drop_column("leads", "page_views")
