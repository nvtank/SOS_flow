from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.entities import RequestStatus, RescueMission, RescueRequest, RescueTeam, TeamStatus
from app.schemas.rescue import (
    AssignRequest,
    MissionOut,
    MissionStatusUpdate,
    RequestStatusOut,
    RescueRequestCreate,
    RescueRequestOut,
    RescueRequestUpdate,
    RescueTeamCreate,
    RescueTeamOut,
    StatisticsOut,
)
from app.services.rescue_service import assign_request, create_rescue_request, update_mission_status

router = APIRouter()


@router.post("/api/rescue-requests", response_model=RescueRequestOut)
def create_request(payload: RescueRequestCreate, db: Session = Depends(get_db)):
    return create_rescue_request(db, payload)


@router.get("/api/rescue-requests/{request_code}/status", response_model=RequestStatusOut)
def get_request_status(request_code: str, db: Session = Depends(get_db)):
    request = db.scalar(select(RescueRequest).where(RescueRequest.request_code == request_code))
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.get("/api/admin/rescue-requests", response_model=list[RescueRequestOut])
def list_requests(
    status: str | None = None,
    priority_level: str | None = None,
    source: str | None = None,
    assigned_team_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(RescueRequest).options(joinedload(RescueRequest.assigned_team))
    if status:
        stmt = stmt.where(RescueRequest.status == status)
    if priority_level:
        stmt = stmt.where(RescueRequest.priority_level == priority_level)
    if source:
        stmt = stmt.where(RescueRequest.source == source)
    if assigned_team_id:
        stmt = stmt.where(RescueRequest.assigned_team_id == assigned_team_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(RescueRequest.request_code.ilike(pattern), RescueRequest.reporter_name.ilike(pattern), RescueRequest.address.ilike(pattern), RescueRequest.message.ilike(pattern)))
    stmt = stmt.order_by(RescueRequest.priority_score.desc(), RescueRequest.created_at.asc())
    return db.scalars(stmt).all()


@router.get("/api/admin/rescue-requests/{request_id}", response_model=RescueRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    request = db.scalar(select(RescueRequest).options(joinedload(RescueRequest.assigned_team)).where(RescueRequest.id == request_id))
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.patch("/api/admin/rescue-requests/{request_id}", response_model=RescueRequestOut)
def update_request(request_id: int, payload: RescueRequestUpdate, db: Session = Depends(get_db)):
    request = db.get(RescueRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    for key, value in payload.model_dump(exclude_unset=True, exclude={"note"}).items():
        setattr(request, key, value)
    db.commit()
    db.refresh(request)
    return request


@router.post("/api/admin/rescue-requests/{request_id}/assign", response_model=MissionOut)
def assign(request_id: int, payload: AssignRequest, db: Session = Depends(get_db)):
    return assign_request(db, request_id, payload.team_id, payload.note)


@router.get("/api/admin/statistics", response_model=StatisticsOut)
def statistics(db: Session = Depends(get_db)):
    active_statuses = [RequestStatus.ASSIGNED.value, RequestStatus.ACCEPTED.value, RequestStatus.MOVING.value, RequestStatus.ARRIVED.value, RequestStatus.RESCUING.value]
    return {
        "total_requests": db.scalar(select(func.count(RescueRequest.id))) or 0,
        "critical_requests": db.scalar(select(func.count(RescueRequest.id)).where(RescueRequest.priority_level == "CRITICAL")) or 0,
        "pending_requests": db.scalar(select(func.count(RescueRequest.id)).where(RescueRequest.status == RequestStatus.PENDING_VERIFICATION.value)) or 0,
        "active_rescues": db.scalar(select(func.count(RescueRequest.id)).where(RescueRequest.status.in_(active_statuses))) or 0,
        "completed_requests": db.scalar(select(func.count(RescueRequest.id)).where(RescueRequest.status == RequestStatus.COMPLETED.value)) or 0,
        "available_teams": db.scalar(select(func.count(RescueTeam.id)).where(RescueTeam.status == TeamStatus.AVAILABLE.value)) or 0,
    }


@router.get("/api/rescue-teams", response_model=list[RescueTeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(RescueTeam).order_by(RescueTeam.id)).all()


@router.post("/api/rescue-teams", response_model=RescueTeamOut)
def create_team(payload: RescueTeamCreate, db: Session = Depends(get_db)):
    team = RescueTeam(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/api/rescue-teams/{team_id}/missions", response_model=list[MissionOut])
def team_missions(team_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(RescueMission)
        .options(joinedload(RescueMission.request).joinedload(RescueRequest.assigned_team), joinedload(RescueMission.team))
        .where(RescueMission.team_id == team_id)
        .order_by(RescueMission.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.patch("/api/missions/{mission_id}/status", response_model=MissionOut)
def patch_mission_status(mission_id: int, payload: MissionStatusUpdate, db: Session = Depends(get_db)):
    return update_mission_status(db, mission_id, payload.status, payload.note)
