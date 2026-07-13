"""Bedrock metadata, team readiness, and mission events

Revision ID: 20260713_03
Revises: 20260713_02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_03"
down_revision = "20260713_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind(); inspector = sa.inspect(bind)
    request_columns = {item["name"] for item in inspector.get_columns("rescue_requests")}
    for name, column in (
        ("ai_metadata", sa.Column("ai_metadata", sa.JSON(), nullable=True)),
        ("ai_fallback_used", sa.Column("ai_fallback_used", sa.Boolean(), nullable=True)),
    ):
        if name not in request_columns: op.add_column("rescue_requests", column)
    false_value = "FALSE" if bind.dialect.name == "postgresql" else "0"
    op.execute(f"UPDATE rescue_requests SET ai_fallback_used = COALESCE(ai_fallback_used, {false_value})")
    if bind.dialect.name == "postgresql":
        op.execute("UPDATE rescue_requests SET ai_metadata = '{}'::json WHERE ai_metadata IS NULL")
    else:
        op.execute("UPDATE rescue_requests SET ai_metadata = '{}' WHERE ai_metadata IS NULL")

    team_columns = {item["name"] for item in inspector.get_columns("rescue_teams")}
    additions = (
        ("capabilities", sa.Column("capabilities", sa.JSON(), nullable=True)), ("equipment", sa.Column("equipment", sa.JSON(), nullable=True)),
        ("max_people_capacity", sa.Column("max_people_capacity", sa.Integer(), nullable=True)), ("current_latitude", sa.Column("current_latitude", sa.Float(), nullable=True)),
        ("current_longitude", sa.Column("current_longitude", sa.Float(), nullable=True)), ("last_location_update", sa.Column("last_location_update", sa.DateTime(timezone=True), nullable=True)),
        ("active_mission_count", sa.Column("active_mission_count", sa.Integer(), nullable=True)),
    )
    for name, column in additions:
        if name not in team_columns: op.add_column("rescue_teams", column)
    op.execute("UPDATE rescue_teams SET active_mission_count = COALESCE(active_mission_count, 0)")
    if bind.dialect.name == "postgresql":
        op.execute("UPDATE rescue_teams SET capabilities = '[]'::json WHERE capabilities IS NULL")
        op.execute("UPDATE rescue_teams SET equipment = '[]'::json WHERE equipment IS NULL")
    else:
        op.execute("UPDATE rescue_teams SET capabilities = '[]' WHERE capabilities IS NULL")
        op.execute("UPDATE rescue_teams SET equipment = '[]' WHERE equipment IS NULL")

    inspector = sa.inspect(bind)
    if "mission_events" not in inspector.get_table_names():
        op.create_table("mission_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("mission_id", sa.Integer(), sa.ForeignKey("rescue_missions.id"), nullable=False), sa.Column("event_type", sa.String(length=40), nullable=False), sa.Column("actor", sa.String(length=120), nullable=False), sa.Column("note", sa.Text(), nullable=True), sa.Column("latitude", sa.Float(), nullable=True), sa.Column("longitude", sa.Float(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
        op.create_index("ix_mission_events_mission_id", "mission_events", ["mission_id"])


def downgrade() -> None:
    pass
