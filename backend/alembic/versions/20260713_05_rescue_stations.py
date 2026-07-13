"""Fixed rescue stations for Tra Linh and Da Nang map operations.

Revision ID: 20260713_05
Revises: 20260713_04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_05"
down_revision = "20260713_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "rescue_stations" not in tables:
        op.create_table(
            "rescue_stations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False, unique=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("area_code", sa.String(length=32), nullable=False),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.text("true") if bind.dialect.name == "postgresql" else sa.text("1")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true") if bind.dialect.name == "postgresql" else sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_rescue_stations_area_code", "rescue_stations", ["area_code"])

    columns = {column["name"] for column in sa.inspect(bind).get_columns("rescue_teams")}
    if "station_id" not in columns:
        with op.batch_alter_table("rescue_teams") as batch:
            batch.add_column(sa.Column("station_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_rescue_teams_station_id", "rescue_stations", ["station_id"], ["id"])
            batch.create_index("ix_rescue_teams_station_id", ["station_id"])


def downgrade() -> None:
    # Do not delete station history or reference data automatically.
    pass
