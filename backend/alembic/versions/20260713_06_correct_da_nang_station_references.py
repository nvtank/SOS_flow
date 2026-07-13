"""Correct simulated station references to Xã Trà Linh and Đà Nẵng.

Revision ID: 20260713_06
Revises: 20260713_05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260713_06"
down_revision = "20260713_05"
branch_labels = None
depends_on = None


STATIONS = (
    ("TRL-01", "Điểm trực demo — UBND Xã Trà Linh", "TRA_LINH", "Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", 15.023565, 108.041263),
    ("DNG-01", "Điểm trực demo — PCCC & CNCH Đà Nẵng", "DA_NANG", "183 Phan Đăng Lưu, thành phố Đà Nẵng", 16.035971, 108.213402),
    ("DNG-02", "Điểm trực demo — Bệnh viện Đà Nẵng", "DA_NANG", "124 Hải Phòng, phường Thạch Thang, thành phố Đà Nẵng", 16.072259, 108.216008),
)


def upgrade() -> None:
    bind = op.get_bind()
    if "rescue_stations" not in sa.inspect(bind).get_table_names():
        return

    update = sa.text(
        """UPDATE rescue_stations
           SET name = :name, area_code = :area_code, address = :address,
               latitude = :latitude, longitude = :longitude, is_active = :is_active
           WHERE code = :code AND is_simulated = :is_simulated"""
    )
    for code, name, area_code, address, latitude, longitude in STATIONS:
        bind.execute(update, {"code": code, "name": name, "area_code": area_code, "address": address,
                              "latitude": latitude, "longitude": longitude, "is_active": True, "is_simulated": True})

    # Previous alpha demo-only placeholders were in the wrong province. Retain them
    # as history but remove them from operational map responses.
    bind.execute(sa.text("UPDATE rescue_stations SET is_active = :inactive WHERE code IN ('TRL-02', 'DNG-03') AND is_simulated = :simulated"), {"inactive": False, "simulated": True})


def downgrade() -> None:
    # Do not restore known-wrong geographic data.
    pass
