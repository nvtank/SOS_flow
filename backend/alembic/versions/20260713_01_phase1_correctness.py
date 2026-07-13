"""phase 1 correctness, integrity and UTC support

Revision ID: 20260713_01
Revises:
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa

from app.db.session import Base
from app.models import entities  # noqa: F401 - register metadata


revision = "20260713_01"
down_revision = None
branch_labels = None
depends_on = None


def _has_index(inspector, table: str, name: str) -> bool:
    return any(index["name"] == name for index in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rescue_requests" not in inspector.get_table_names():
        # A clean database receives the complete current schema in one revision.
        Base.metadata.create_all(bind=bind)
        return

    columns = {column["name"] for column in inspector.get_columns("rescue_requests")}
    if "priority_calculated_at" not in columns:
        op.add_column("rescue_requests", sa.Column("priority_calculated_at", sa.DateTime(timezone=True), nullable=True))
        op.execute("UPDATE rescue_requests SET priority_calculated_at = COALESCE(updated_at, created_at)")

    inspector = sa.inspect(bind)
    indexes = [
        ("rescue_requests", "ix_rescue_requests_created_at", ["created_at"]),
        ("rescue_requests", "ix_rescue_requests_source", ["source"]),
        ("rescue_requests", "ix_rescue_requests_assigned_team_id", ["assigned_team_id"]),
    ]
    for table, name, columns in indexes:
        if not _has_index(inspector, table, name):
            op.create_index(name, table, columns)

    # Partial unique indexes make active mission uniqueness durable even if two
    # API workers race. SQLite and PostgreSQL both support this expression.
    if not _has_index(inspector, "rescue_missions", "uq_active_mission_per_request"):
        op.create_index(
            "uq_active_mission_per_request",
            "rescue_missions",
            ["request_id"],
            unique=True,
            sqlite_where=sa.text("status NOT IN ('COMPLETED', 'FAILED')"),
            postgresql_where=sa.text("status NOT IN ('COMPLETED', 'FAILED')"),
        )
    if not _has_index(inspector, "rescue_missions", "uq_active_mission_per_team"):
        op.create_index(
            "uq_active_mission_per_team",
            "rescue_missions",
            ["team_id"],
            unique=True,
            sqlite_where=sa.text("status NOT IN ('COMPLETED', 'FAILED')"),
            postgresql_where=sa.text("status NOT IN ('COMPLETED', 'FAILED')"),
        )

    # Existing PostgreSQL data was written as UTC by the old app. Convert its
    # storage type without reinterpreting wall-clock values. SQLite has no real
    # timezone type; the API treats legacy values as UTC during serialization.
    if bind.dialect.name == "postgresql":
        for table, column in (
            ("rescue_requests", "created_at"), ("rescue_requests", "updated_at"), ("rescue_requests", "priority_calculated_at"),
            ("rescue_teams", "created_at"), ("rescue_teams", "updated_at"),
            ("rescue_missions", "assigned_at"), ("rescue_missions", "accepted_at"), ("rescue_missions", "arrived_at"),
            ("rescue_missions", "completed_at"), ("rescue_missions", "created_at"), ("rescue_missions", "updated_at"),
            ("status_history", "created_at"),
        ):
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE USING {column} AT TIME ZONE \'UTC\'')


def downgrade() -> None:
    # Data preservation is more valuable than trying to reverse timezone casts.
    # The initial revision deliberately does not drop user data or constraints.
    pass
