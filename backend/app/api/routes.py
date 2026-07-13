from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.entities import RequestStatus, RescueMission, RescueRequest, RescueStation, RescueTeam, SilentZoneHistory, StatusHistory, TeamStatus
from app.schemas.rescue import (
    AssignRequest,
    DuplicateCandidateOut,
    DuplicateDecision,
    DuplicateSummaryOut,
    MergeDuplicateRequest,
    MissionEventOut,
    MissionOut,
    MissionStatusUpdate,
    PaginatedRescueRequests,
    RequestStatusOut,
    RescueRequestCreate,
    RescueRequestOut,
    RescueRequestUpdate,
    RescueTeamCreate,
    RescueTeamOut,
    RescueStationOut,
    StatisticsOut,
    StatusHistoryOut,
    TeamRecommendationOut,
    SilentZoneHistoryOut,
    SilentZoneOut,
    SilentZoneStatusUpdate,
)
from app.services.rescue_service import (
    assign_request,
    reanalyze_request,
    refresh_open_priorities,
    update_mission_status,
    update_rescue_request,
)
from app.services.duplicate_service import decide_duplicate, duplicate_summary, list_duplicate_candidates, merge_duplicate_report
from app.services.intake_service import intake_rescue_request
from app.services.statistics_service import get_operational_statistics
from app.services.dispatch_recommendation_service import recommend_teams
from app.services.silent_zone_service import list_silent_zones, update_verification

router = APIRouter()


@router.post("/api/rescue-requests", response_model=RescueRequestOut)
def create_request(payload: RescueRequestCreate, db: Session = Depends(get_db)):
    request, _ = intake_rescue_request(db, payload, simulated=False)
    return request


@router.get("/api/rescue-requests/{request_code}/status", response_model=RequestStatusOut)
def get_request_status(request_code: str, db: Session = Depends(get_db)):
    request = db.scalar(select(RescueRequest).where(RescueRequest.request_code == request_code))
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request


@router.get("/api/admin/rescue-requests", response_model=PaginatedRescueRequests)
def list_requests(
    status: str | None = None,
    priority_level: str | None = None,
    source: str | None = None,
    assigned_team_id: int | None = None,
    assignment: str | None = Query(default=None, pattern="^(assigned|unassigned)$"),
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="priority_score"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    # Aging is persisted only once per bounded refresh interval, never for each GET.
    refresh_open_priorities(db)
    stmt = select(RescueRequest).options(joinedload(RescueRequest.assigned_team))
    if status:
        stmt = stmt.where(RescueRequest.status == status)
    if priority_level:
        stmt = stmt.where(RescueRequest.priority_level == priority_level)
    if source:
        stmt = stmt.where(RescueRequest.source == source)
    if assigned_team_id is not None:
        stmt = stmt.where(RescueRequest.assigned_team_id == assigned_team_id)
    if assignment == "assigned":
        stmt = stmt.where(RescueRequest.assigned_team_id.is_not(None))
    if assignment == "unassigned":
        stmt = stmt.where(RescueRequest.assigned_team_id.is_(None))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                RescueRequest.request_code.ilike(pattern),
                RescueRequest.reporter_name.ilike(pattern),
                RescueRequest.address.ilike(pattern),
                RescueRequest.message.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    sort_columns = {
        "priority_score": RescueRequest.priority_score,
        "created_at": RescueRequest.created_at,
        "updated_at": RescueRequest.updated_at,
        "request_code": RescueRequest.request_code,
        "status": RescueRequest.status,
        "priority_level": RescueRequest.priority_level,
    }
    column = sort_columns.get(sort_by)
    if column is None:
        raise HTTPException(status_code=422, detail=f"Unsupported sort_by: {sort_by}")
    ordering = column.asc() if sort_order == "asc" else column.desc()
    items = db.scalars(
        stmt.order_by(ordering, RescueRequest.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.get("/api/admin/rescue-requests/{request_id}", response_model=RescueRequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    refresh_open_priorities(db)
    request = db.scalar(select(RescueRequest).options(joinedload(RescueRequest.assigned_team)).where(RescueRequest.id == request_id))
    if not request:
        raise HTTPException(status_code=404, detail="Rescue request not found")
    return request


@router.patch("/api/admin/rescue-requests/{request_id}", response_model=RescueRequestOut)
def update_request(request_id: int, payload: RescueRequestUpdate, db: Session = Depends(get_db)):
    return update_rescue_request(db, request_id, payload)


@router.post("/api/admin/rescue-requests/{request_id}/reanalyze", response_model=RescueRequestOut)
def reanalyze(request_id: int, db: Session = Depends(get_db)):
    return reanalyze_request(db, request_id)


@router.get("/api/admin/rescue-requests/{request_id}/team-recommendations", response_model=list[TeamRecommendationOut])
def team_recommendations(request_id: int, db: Session = Depends(get_db)):
    try:
        return recommend_teams(db, request_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/api/admin/rescue-requests/{request_id}/timeline", response_model=list[StatusHistoryOut])
def request_timeline(request_id: int, db: Session = Depends(get_db)):
    if not db.get(RescueRequest, request_id):
        raise HTTPException(status_code=404, detail="Rescue request not found")
    return db.scalars(
        select(StatusHistory).where(StatusHistory.request_id == request_id).order_by(StatusHistory.created_at.asc(), StatusHistory.id.asc())
    ).all()


@router.get("/api/admin/rescue-requests/{request_id}/duplicates", response_model=list[DuplicateCandidateOut])
def request_duplicates(request_id: int, db: Session = Depends(get_db)):
    return list_duplicate_candidates(db, request_id)


@router.get("/api/admin/rescue-requests/{request_id}/duplicate-summary", response_model=DuplicateSummaryOut)
def request_duplicate_summary(request_id: int, db: Session = Depends(get_db)):
    return duplicate_summary(db, request_id)


@router.post("/api/admin/rescue-requests/{request_id}/duplicates/{candidate_id}/confirm", response_model=DuplicateCandidateOut)
def confirm_duplicate(request_id: int, candidate_id: int, payload: DuplicateDecision, db: Session = Depends(get_db)):
    return decide_duplicate(db, request_id, candidate_id, confirmed=True, note=payload.note)


@router.post("/api/admin/rescue-requests/{request_id}/duplicates/{candidate_id}/reject", response_model=DuplicateCandidateOut)
def reject_duplicate(request_id: int, candidate_id: int, payload: DuplicateDecision, db: Session = Depends(get_db)):
    return decide_duplicate(db, request_id, candidate_id, confirmed=False, note=payload.note)


@router.post("/api/admin/rescue-requests/{request_id}/merge", response_model=RescueRequestOut)
def merge_duplicate(request_id: int, payload: MergeDuplicateRequest, db: Session = Depends(get_db)):
    return merge_duplicate_report(db, request_id, payload.canonical_request_id, payload.candidate_id, payload.note)


@router.post("/api/admin/rescue-requests/{request_id}/assign", response_model=MissionOut)
def assign(request_id: int, payload: AssignRequest, db: Session = Depends(get_db)):
    return assign_request(db, request_id, payload.team_id, payload.note)


@router.get("/api/admin/statistics", response_model=StatisticsOut)
def statistics(db: Session = Depends(get_db)):
    refresh_open_priorities(db)
    return get_operational_statistics(db)


@router.get("/api/admin/silent-zones", response_model=list[SilentZoneOut])
def silent_zones(alerts_only: bool = False, db: Session = Depends(get_db)):
    return list_silent_zones(db, only_alerts=alerts_only)


@router.patch("/api/admin/silent-zones/{zone_id}/verification", response_model=SilentZoneOut)
def update_silent_zone(zone_id: int, payload: SilentZoneStatusUpdate, db: Session = Depends(get_db)):
    return update_verification(db, zone_id, payload.status, payload.note)


@router.get("/api/admin/silent-zones/{zone_id}/timeline", response_model=list[SilentZoneHistoryOut])
def silent_zone_timeline(zone_id: int, db: Session = Depends(get_db)):
    return db.scalars(select(SilentZoneHistory).where(SilentZoneHistory.zone_id == zone_id).order_by(SilentZoneHistory.created_at)).all()


@router.get("/api/rescue-teams", response_model=list[RescueTeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(RescueTeam).options(joinedload(RescueTeam.station)).order_by(RescueTeam.id)).all()


@router.get("/api/rescue-stations", response_model=list[RescueStationOut])
def list_rescue_stations(area_code: str | None = None, db: Session = Depends(get_db)):
    stmt = select(RescueStation).where(RescueStation.is_active.is_(True))
    if area_code:
        stmt = stmt.where(RescueStation.area_code == area_code.upper())
    return db.scalars(stmt.order_by(RescueStation.area_code, RescueStation.code)).all()


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


@router.get("/api/missions/{mission_id}/events", response_model=list[MissionEventOut])
def mission_events(mission_id: int, db: Session = Depends(get_db)):
    mission = db.get(RescueMission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission.events


@router.patch("/api/missions/{mission_id}/status", response_model=MissionOut)
def patch_mission_status(mission_id: int, payload: MissionStatusUpdate, db: Session = Depends(get_db)):
    return update_mission_status(db, mission_id, payload.status, payload.note, payload.latitude, payload.longitude)
