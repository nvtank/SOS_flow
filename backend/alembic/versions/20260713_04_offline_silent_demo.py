"""Offline sync timestamps, silent zones, and demo scenario state.

Revision ID: 20260713_04
Revises: 20260713_03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_04"
down_revision = "20260713_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind(); inspector = sa.inspect(bind)
    request_columns = {item["name"] for item in inspector.get_columns("rescue_requests")}
    if "synced_at" not in request_columns:
        op.add_column("rescue_requests", sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True))
        op.execute("UPDATE rescue_requests SET synced_at = COALESCE(updated_at, created_at, received_at)")

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "silent_zones" not in tables:
        op.create_table(
            "silent_zones", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("scenario_key", sa.String(length=80), nullable=True), sa.Column("latitude", sa.Float(), nullable=False), sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("radius_meters", sa.Integer(), nullable=False), sa.Column("hazard_active", sa.Boolean(), nullable=False), sa.Column("last_report_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("silence_threshold_minutes", sa.Integer(), nullable=False), sa.Column("verification_status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_silent_zones_scenario_key", "silent_zones", ["scenario_key"])
    if "silent_zone_history" not in tables:
        op.create_table(
            "silent_zone_history", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("zone_id", sa.Integer(), sa.ForeignKey("silent_zones.id"), nullable=False),
            sa.Column("old_status", sa.String(length=32), nullable=True), sa.Column("new_status", sa.String(length=32), nullable=False), sa.Column("actor", sa.String(length=120), nullable=False),
            sa.Column("note", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_silent_zone_history_zone_id", "silent_zone_history", ["zone_id"])
    if "demo_scenario_states" not in tables:
        op.create_table(
            "demo_scenario_states", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("scenario_key", sa.String(length=80), nullable=False, unique=True),
            sa.Column("next_event", sa.Integer(), nullable=False), sa.Column("paused", sa.Boolean(), nullable=False), sa.Column("speed", sa.Integer(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_demo_scenario_states_scenario_key", "demo_scenario_states", ["scenario_key"])


def downgrade() -> None:
    # Scenario/audit data should not be destructively removed by downgrade.
    pass
