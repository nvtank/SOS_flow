"""Silent-zone verification signals; never infer that people are in danger."""

from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import as_utc, utc_now
from app.models.entities import SilentZone, SilentZoneHistory, SilentZoneVerificationStatus


def _distance_meters(latitude: float, longitude: float, zone: SilentZone) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (latitude, longitude, zone.latitude, zone.longitude))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * asin(sqrt(a))


def note_report(db: Session, latitude: float | None, longitude: float | None, reported_at=None) -> None:
    """Record contact only for zones containing a report; this does not verify safety."""
    if latitude is None or longitude is None:
        return
    for zone in db.scalars(select(SilentZone).where(SilentZone.hazard_active.is_(True))).all():
        if _distance_meters(latitude, longitude, zone) <= zone.radius_meters:
            zone.last_report_at = as_utc(reported_at or utc_now())


def list_silent_zones(db: Session, only_alerts: bool = False, now=None) -> list[dict]:
    current = as_utc(now or utc_now())
    items: list[dict] = []
    for zone in db.scalars(select(SilentZone).order_by(SilentZone.name)).all():
        minutes = None if zone.last_report_at is None else max(0, (current - as_utc(zone.last_report_at)).total_seconds() / 60)
        stale = zone.hazard_active and (minutes is None or minutes >= zone.silence_threshold_minutes)
        if only_alerts and not stale:
            continue
        data = {
            "id": zone.id, "name": zone.name, "scenario_key": zone.scenario_key, "latitude": zone.latitude, "longitude": zone.longitude,
            "radius_meters": zone.radius_meters, "hazard_active": zone.hazard_active, "last_report_at": zone.last_report_at,
            "silence_threshold_minutes": zone.silence_threshold_minutes, "verification_status": zone.verification_status,
            "silence_minutes": round(minutes, 1) if minutes is not None else None,
            "reason": "Khu vực có hazard đang hoạt động nhưng chưa có tin báo trong ngưỡng cần xác minh" if stale else None,
            "created_at": zone.created_at, "updated_at": zone.updated_at,
        }
        items.append(data)
    return items


def update_verification(db: Session, zone_id: int, status: str, note: str | None, actor: str = "admin") -> SilentZone:
    if status not in {item.value for item in SilentZoneVerificationStatus}:
        raise HTTPException(status_code=422, detail="Invalid silent zone verification status")
    zone = db.get(SilentZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Silent zone not found")
    old_status = zone.verification_status
    zone.verification_status = status
    db.add(SilentZoneHistory(zone_id=zone.id, old_status=old_status, new_status=status, actor=actor, note=note))
    db.commit(); db.refresh(zone)
    return zone
