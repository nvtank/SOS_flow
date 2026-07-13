from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models.entities import MissionStatus, RequestStatus, RescueMission, RescueRequest, RescueTeam, StatusHistory, TeamStatus
from app.schemas.rescue import RescueRequestCreate
from app.services.ai_analyzer import MockEmergencyAnalyzer
from app.services.priority_engine import PriorityEngine, PriorityInput


def _next_request_code(db: Session) -> str:
    count = db.scalar(select(func.count(RescueRequest.id))) or 0
    return f"SOS-{count + 1:04d}"


def create_rescue_request(db: Session, payload: RescueRequestCreate) -> RescueRequest:
    analyzer = MockEmergencyAnalyzer()
    settings = get_settings()
    engine = PriorityEngine(settings.rules_path)
    created_at = datetime.utcnow()
    priority = engine.calculate(PriorityInput(**payload.model_dump(exclude={"note", "source"}), created_at=created_at))
    request = RescueRequest(
        request_code=_next_request_code(db),
        **payload.model_dump(exclude={"note"}),
        ai_analysis=analyzer.analyze(payload.message),
        priority_score=priority["priority_score"],
        priority_level=priority["priority_level"],
        priority_reasons=priority["reasons"],
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(request)
    db.flush()
    db.add(StatusHistory(request_id=request.id, old_status=None, new_status=request.status, changed_by="reporter", note=payload.note))
    db.commit()
    db.refresh(request)
    return request


def assign_request(db: Session, request_id: int, team_id: int, note: str | None = None) -> RescueMission:
    request = db.get(RescueRequest, request_id)
    team = db.get(RescueTeam, team_id)
    if not request:
        raise HTTPException(status_code=404, detail="Rescue request not found")
    if not team:
        raise HTTPException(status_code=404, detail="Rescue team not found")
    if team.status == TeamStatus.OFFLINE.value:
        raise HTTPException(status_code=400, detail="Cannot assign an offline team")

    old_status = request.status
    request.status = RequestStatus.ASSIGNED.value
    request.assigned_team_id = team.id
    team.status = TeamStatus.BUSY.value
    mission = RescueMission(request_id=request.id, team_id=team.id, status=MissionStatus.ASSIGNED.value, notes=note)
    db.add(mission)
    db.add(StatusHistory(request_id=request.id, old_status=old_status, new_status=request.status, changed_by="admin", note=note))
    db.commit()
    return db.scalar(select(RescueMission).options(joinedload(RescueMission.request), joinedload(RescueMission.team)).where(RescueMission.id == mission.id))


def update_mission_status(db: Session, mission_id: int, status: str, note: str | None = None) -> RescueMission:
    mission = db.scalar(
        select(RescueMission)
        .options(joinedload(RescueMission.request), joinedload(RescueMission.team))
        .where(RescueMission.id == mission_id)
    )
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if status not in {item.value for item in MissionStatus}:
        raise HTTPException(status_code=400, detail="Invalid mission status")

    old_status = mission.request.status
    mission.status = status
    mission.notes = "\n".join(filter(None, [mission.notes, note]))
    now = datetime.utcnow()
    if status == MissionStatus.ACCEPTED.value:
        mission.accepted_at = now
    if status == MissionStatus.ARRIVED.value:
        mission.arrived_at = now
    if status in {MissionStatus.COMPLETED.value, MissionStatus.FAILED.value}:
        mission.completed_at = now
        mission.team.status = TeamStatus.AVAILABLE.value
    mission.request.status = status
    db.add(StatusHistory(request_id=mission.request_id, old_status=old_status, new_status=status, changed_by="rescue_team", note=note))
    db.commit()
    db.refresh(mission)
    return mission
