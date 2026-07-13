"""Persist structured versus Bedrock natural-language intake mode."""

from alembic import op
import sqlalchemy as sa


revision = "20260714_07"
down_revision = "20260713_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rescue_requests",
        sa.Column("intake_mode", sa.String(length=32), nullable=False, server_default="NATURAL_LANGUAGE"),
    )
    op.create_index("ix_rescue_requests_intake_mode", "rescue_requests", ["intake_mode"])


def downgrade() -> None:
    op.drop_index("ix_rescue_requests_intake_mode", table_name="rescue_requests")
    op.drop_column("rescue_requests", "intake_mode")
