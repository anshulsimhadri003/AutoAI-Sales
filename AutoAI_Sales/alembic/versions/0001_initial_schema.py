"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "dealerships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "worker_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dealership_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("worker_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("tagline", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
    )
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dealership_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("source_channel", sa.String(length=50), nullable=False),
        sa.Column("vehicle_interest", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=2000), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.String(length=20), nullable=False),
        sa.Column("urgency", sa.String(length=30), nullable=False),
        sa.Column("assigned_rep", sa.String(length=100), nullable=False),
        sa.Column("next_action", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dealership_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("lead_name", sa.String(length=255), nullable=False),
        sa.Column("lead_public_id", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("engagement", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("next_step", sa.String(length=255), nullable=False),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dealership_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("public_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("lead_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column("rep_id", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.String(length=64), nullable=False),
        sa.Column("end_time", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("sequences")
    op.drop_table("leads")
    op.drop_table("worker_configs")
    op.drop_table("dealerships")
