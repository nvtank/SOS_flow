"""Database-aggregated operational metrics for the Command Center."""

from datetime import timedelta

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.entities import DuplicateCandidate, DuplicateState, RequestStatus, RescueRequest, RescueTeam, StatusHistory, TeamStatus
from app.services.silent_zone_service import list_silent_zones


ACTIVE_STATUSES = [RequestStatus.ASSIGNED.value, RequestStatus.ACCEPTED.value, RequestStatus.MOVING.value, RequestStatus.BLOCKED.value, RequestStatus.ARRIVED.value, RequestStatus.RESCUING.value, RequestStatus.NEED_REINFORCEMENT.value]


def _count(db: Session, *conditions) -> int:
    return db.scalar(select(func.count(RescueRequest.id)).where(*conditions)) or 0


def _distribution(db: Session, column) -> list[dict]:
    rows = db.execute(select(column, func.count(RescueRequest.id)).group_by(column).order_by(func.count(RescueRequest.id).desc())).all()
    return [{"label": str(label), "value": int(value)} for label, value in rows]


def _time_series(db: Session, minutes: bool) -> list[dict]:
    now = utc_now()
    window = now - (timedelta(hours=1) if minutes else timedelta(hours=24))
    if db.bind and db.bind.dialect.name == "postgresql":
        truncated = func.date_trunc("minute" if minutes else "hour", RescueRequest.received_at)
        bucket = func.to_char(truncated, 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
    else:
        bucket = func.strftime("%Y-%m-%dT%H:%M:00Z" if minutes else "%Y-%m-%dT%H:00:00Z", RescueRequest.received_at)
    rows = db.execute(
        select(bucket.label("bucket"), func.count(RescueRequest.id).label("value"))
        .where(RescueRequest.received_at >= window)
        .group_by(bucket)
        .order_by(bucket)
    ).all()
    return [{"bucket": str(item.bucket), "value": int(item.value)} for item in rows]


def _average_minutes(db: Session, end_at) -> float | None:
    if db.bind and db.bind.dialect.name == "postgresql":
        minutes = func.extract("epoch", end_at - RescueRequest.received_at) / 60
    else:
        minutes = (func.julianday(end_at) - func.julianday(RescueRequest.received_at)) * 1440
    value = db.scalar(select(func.avg(minutes)).where(end_at.is_not(None)))
    return round(float(value), 1) if value is not None else None


def get_operational_statistics(db: Session) -> dict:
    now = utc_now()
    assigned_at = select(func.min(StatusHistory.created_at)).where(StatusHistory.request_id == RescueRequest.id, StatusHistory.new_status == RequestStatus.ASSIGNED.value).scalar_subquery()
    arrived_at = select(func.min(StatusHistory.created_at)).where(StatusHistory.request_id == RescueRequest.id, StatusHistory.new_status == RequestStatus.ARRIVED.value).scalar_subquery()
    completed_at = select(func.min(StatusHistory.created_at)).where(StatusHistory.request_id == RescueRequest.id, StatusHistory.new_status == RequestStatus.COMPLETED.value).scalar_subquery()
    if db.bind and db.bind.dialect.name == "postgresql":
        waiting_expr = func.extract("epoch", literal(now) - RescueRequest.received_at) / 60
    else:
        waiting_expr = (func.julianday(literal(now)) - func.julianday(RescueRequest.received_at)) * 1440

    pending = _count(db, RescueRequest.status == RequestStatus.PENDING_VERIFICATION.value)
    critical = _count(db, RescueRequest.priority_level == "CRITICAL")
    unassigned_critical = _count(db, RescueRequest.priority_level == "CRITICAL", RescueRequest.assigned_team_id.is_(None), RescueRequest.status.not_in([RequestStatus.COMPLETED.value, RequestStatus.FAILED.value]))
    missing_location = _count(db, or_(RescueRequest.latitude.is_(None), RescueRequest.longitude.is_(None)))
    duplicate_count = db.scalar(select(func.count(DuplicateCandidate.id)).where(DuplicateCandidate.status == DuplicateState.POSSIBLE_DUPLICATE.value)) or 0
    active = _count(db, RescueRequest.status.in_(ACTIVE_STATUSES))
    completed = _count(db, RescueRequest.status == RequestStatus.COMPLETED.value)
    failed = _count(db, RescueRequest.status == RequestStatus.FAILED.value)
    blocked = _count(db, RescueRequest.status == RequestStatus.BLOCKED.value)
    reinforcement = _count(db, RescueRequest.status == RequestStatus.NEED_REINFORCEMENT.value)
    silent_zone_alerts = len(list_silent_zones(db, only_alerts=True, now=now))
    averages_waiting = db.scalar(select(func.avg(waiting_expr)).where(RescueRequest.status.not_in([RequestStatus.COMPLETED.value, RequestStatus.FAILED.value])))

    alerts = []
    for key, label, count, severity in (
        ("unassigned_critical", "Critical chưa phân công", unassigned_critical, "CRITICAL"),
        ("pending_verification", "Tin chờ xác minh", pending, "HIGH"),
        ("duplicate_candidates", "Nghi trùng cần quyết định", duplicate_count, "MEDIUM"),
        ("missing_location", "Tin thiếu vị trí", missing_location, "MEDIUM"),
        ("blocked", "Nhiệm vụ bị chặn tuyến", blocked, "HIGH"),
        ("reinforcement", "Nhiệm vụ cần tăng cường", reinforcement, "CRITICAL"),
        ("silent_zones", "Vùng im lặng cần xác minh", silent_zone_alerts, "HIGH"),
    ):
        if count:
            alerts.append({"key": key, "label": label, "count": int(count), "severity": severity})

    return {
        "total_requests": _count(db),
        "critical_requests": critical,
        "high_requests": _count(db, RescueRequest.priority_level == "HIGH"),
        "pending_verification": pending,
        "pending_requests": pending,
        "verified": _count(db, RescueRequest.status == RequestStatus.VERIFIED.value),
        "assigned": _count(db, RescueRequest.status == RequestStatus.ASSIGNED.value),
        "active_rescues": active,
        "completed_requests": completed,
        "completed": completed,
        "failed": failed,
        "blocked_rescues": blocked,
        "reinforcement_rescues": reinforcement,
        "available_teams": db.scalar(select(func.count(RescueTeam.id)).where(RescueTeam.status == TeamStatus.AVAILABLE.value)) or 0,
        "busy_teams": db.scalar(select(func.count(RescueTeam.id)).where(RescueTeam.status == TeamStatus.BUSY.value)) or 0,
        "offline_teams": db.scalar(select(func.count(RescueTeam.id)).where(RescueTeam.status == TeamStatus.OFFLINE.value)) or 0,
        "requests_by_priority": _distribution(db, RescueRequest.priority_level),
        "requests_by_status": _distribution(db, RescueRequest.status),
        "requests_by_source": _distribution(db, RescueRequest.source),
        "requests_over_time": _time_series(db, minutes=False),
        "requests_over_time_minutes": _time_series(db, minutes=True) if get_settings().demo_mode else [],
        "average_waiting_minutes": round(float(averages_waiting), 1) if averages_waiting is not None else 0.0,
        "average_time_to_assign": _average_minutes(db, assigned_at),
        "average_time_to_arrive": _average_minutes(db, arrived_at),
        "average_completion_time": _average_minutes(db, completed_at),
        "missing_location_count": missing_location,
        "duplicate_candidates_count": int(duplicate_count),
        "unassigned_critical_count": unassigned_critical,
        "silent_zone_alerts_count": silent_zone_alerts,
        "action_alerts": alerts,
    }
