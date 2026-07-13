"""multi-source intake simulation and duplicate candidates

Revision ID: 20260713_02
Revises: 20260713_01
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_02"
down_revision = "20260713_01"
branch_labels = None
depends_on = None


def _has_index(inspector, table: str, name: str) -> bool:
    return any(index["name"] == name for index in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("rescue_requests")}
    additions = (
        ("external_reference", sa.Column("external_reference", sa.String(length=160), nullable=True)),
        ("client_submission_id", sa.Column("client_submission_id", sa.String(length=160), nullable=True)),
        ("received_at", sa.Column("received_at", sa.DateTime(timezone=True), nullable=True)),
        ("is_simulated", sa.Column("is_simulated", sa.Boolean(), nullable=True)),
        ("raw_payload", sa.Column("raw_payload", sa.JSON(), nullable=True)),
        ("canonical_request_id", sa.Column("canonical_request_id", sa.Integer(), nullable=True)),
        ("duplicate_state", sa.Column("duplicate_state", sa.String(length=32), nullable=True)),
    )
    for name, column in additions:
        if name not in existing_columns:
            op.add_column("rescue_requests", column)

    op.execute("UPDATE rescue_requests SET received_at = COALESCE(received_at, created_at)")
    false_value = "FALSE" if bind.dialect.name == "postgresql" else "0"
    op.execute(f"UPDATE rescue_requests SET is_simulated = COALESCE(is_simulated, {false_value})")
    op.execute("UPDATE rescue_requests SET duplicate_state = COALESCE(duplicate_state, 'NOT_DUPLICATE')")

    inspector = sa.inspect(bind)
    if not _has_index(inspector, "rescue_requests", "ix_rescue_requests_duplicate_state"):
        op.create_index("ix_rescue_requests_duplicate_state", "rescue_requests", ["duplicate_state"])
    if not _has_index(inspector, "rescue_requests", "uq_rescue_requests_client_submission_id"):
        op.create_index(
            "uq_rescue_requests_client_submission_id", "rescue_requests", ["client_submission_id"], unique=True,
            sqlite_where=sa.text("client_submission_id IS NOT NULL"), postgresql_where=sa.text("client_submission_id IS NOT NULL"),
        )
    if not _has_index(inspector, "rescue_requests", "uq_rescue_requests_source_external_reference"):
        op.create_index(
            "uq_rescue_requests_source_external_reference", "rescue_requests", ["source", "external_reference"], unique=True,
            sqlite_where=sa.text("external_reference IS NOT NULL"), postgresql_where=sa.text("external_reference IS NOT NULL"),
        )

    if "duplicate_candidates" not in inspector.get_table_names():
        op.create_table(
            "duplicate_candidates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("request_id", sa.Integer(), sa.ForeignKey("rescue_requests.id"), nullable=False),
            sa.Column("candidate_request_id", sa.Integer(), sa.ForeignKey("rescue_requests.id"), nullable=False),
            sa.Column("duplicate_score", sa.Float(), nullable=False),
            sa.Column("reasons", sa.JSON(), nullable=False),
            sa.Column("confidence_level", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("decided_by", sa.String(length=120), nullable=True),
            sa.Column("decision_note", sa.Text(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("request_id", "candidate_request_id", name="uq_duplicate_candidate_pair"),
        )
        op.create_index("ix_duplicate_candidates_status", "duplicate_candidates", ["status"])
        op.create_index("ix_duplicate_candidates_request_id", "duplicate_candidates", ["request_id"])
        op.create_index("ix_duplicate_candidates_candidate_request_id", "duplicate_candidates", ["candidate_request_id"])


def downgrade() -> None:
    # Preserve reports and duplicate audit data; destructive downgrade is intentionally omitted.
    pass
