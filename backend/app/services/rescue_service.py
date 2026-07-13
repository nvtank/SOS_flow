"""Transactional domain operations for rescue requests and missions."""

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.time import as_utc, utc_now
from app.models.entities import IntakeMode, MissionEvent, MissionStatus, RequestStatus, RescueMission, RescueRequest, RescueTeam, StatusHistory, TeamStatus
from app.schemas.rescue import RescueRequestCreate, RescueRequestUpdate
from app.services.ai_analyzer import analyze_with_fallback
from app.services.geocoding_service import suggest_demo_coordinates
from app.services.priority_engine import PriorityEngine, PriorityInput


TERMINAL_STATUSES = {RequestStatus.COMPLETED.value, RequestStatus.FAILED.value}
ACTIVE_MISSION_STATUSES = {item.value for item in MissionStatus} - TERMINAL_STATUSES

# Request states advance only one step.  Team progress uses the equivalent
# mission matrix below and is the only way to move a request beyond ASSIGNED.
REQUEST_TRANSITIONS = {
    RequestStatus.PENDING_VERIFICATION.value: {RequestStatus.VERIFIED.value},
    RequestStatus.VERIFIED.value: {RequestStatus.ASSIGNED.value},
    RequestStatus.ASSIGNED.value: {RequestStatus.ACCEPTED.value},
    RequestStatus.ACCEPTED.value: {RequestStatus.MOVING.value},
    RequestStatus.MOVING.value: {RequestStatus.ARRIVED.value, RequestStatus.BLOCKED.value},
    RequestStatus.BLOCKED.value: {RequestStatus.MOVING.value, RequestStatus.FAILED.value},
    RequestStatus.ARRIVED.value: {RequestStatus.RESCUING.value, RequestStatus.NEED_REINFORCEMENT.value},
    RequestStatus.RESCUING.value: {RequestStatus.COMPLETED.value, RequestStatus.FAILED.value, RequestStatus.NEED_REINFORCEMENT.value},
    RequestStatus.NEED_REINFORCEMENT.value: {RequestStatus.RESCUING.value, RequestStatus.FAILED.value},
    RequestStatus.COMPLETED.value: set(),
    RequestStatus.FAILED.value: set(),
}
MISSION_TRANSITIONS = {
    MissionStatus.ASSIGNED.value: {MissionStatus.ACCEPTED.value},
    MissionStatus.ACCEPTED.value: {MissionStatus.MOVING.value},
    MissionStatus.MOVING.value: {MissionStatus.ARRIVED.value, MissionStatus.BLOCKED.value},
    MissionStatus.BLOCKED.value: {MissionStatus.MOVING.value, MissionStatus.FAILED.value},
    MissionStatus.ARRIVED.value: {MissionStatus.RESCUING.value, MissionStatus.NEED_REINFORCEMENT.value},
    MissionStatus.RESCUING.value: {MissionStatus.COMPLETED.value, MissionStatus.FAILED.value, MissionStatus.NEED_REINFORCEMENT.value},
    MissionStatus.NEED_REINFORCEMENT.value: {MissionStatus.RESCUING.value, MissionStatus.FAILED.value},
    MissionStatus.COMPLETED.value: set(),
    MissionStatus.FAILED.value: set(),
}
PRIORITY_INPUT_FIELDS = {
    "message",
    "number_of_people",
    "number_of_children",
    "number_of_elderly",
    "number_of_injured",
    "has_disabled_person",
    "has_pregnant_person",
    "is_trapped",
    "water_level",
}

# Reporter can submit only a free-text SOS message. These values are populated
# from a sufficiently confident AI suggestion only when that field was absent
# from the original payload. Operator edits and explicit reporter values always
# take precedence; re-analysis remains suggestion-only.
AI_AUTOFILL_CONFIDENCE = 0.65
AI_AUTOFILL_FIELDS = (
    "number_of_people",
    "number_of_children",
    "number_of_elderly",
    "number_of_injured",
    "is_trapped",
    "water_level",
)


def _engine() -> PriorityEngine:
    return PriorityEngine(get_settings().rules_path)


def _priority_input(request: RescueRequest) -> PriorityInput:
    return PriorityInput(
        message=request.message,
        number_of_people=request.number_of_people,
        number_of_children=request.number_of_children,
        number_of_elderly=request.number_of_elderly,
        number_of_injured=request.number_of_injured,
        has_disabled_person=request.has_disabled_person,
        has_pregnant_person=request.has_pregnant_person,
        is_trapped=request.is_trapped,
        water_level=request.water_level,
        created_at=request.created_at,
    )


def _apply_priority(request: RescueRequest, now: datetime) -> bool:
    priority = _engine().calculate(_priority_input(request), now=now)
    changed = any(
        getattr(request, column) != priority[source]
        for column, source in (
            ("priority_score", "priority_score"),
            ("priority_level", "priority_level"),
            ("priority_reasons", "reasons"),
        )
    )
    request.priority_score = priority["priority_score"]
    request.priority_level = priority["priority_level"]
    request.priority_reasons = priority["reasons"]
    request.priority_calculated_at = now
    return changed


def _record_history(
    db: Session,
    request: RescueRequest,
    old_status: str | None,
    new_status: str,
    changed_by: str,
    note: str | None = None,
) -> None:
    db.add(
        StatusHistory(
            request_id=request.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            note=note,
        )
    )


def _record_mission_event(db: Session, mission: RescueMission, event_type: str, actor: str, note: str | None = None, latitude: float | None = None, longitude: float | None = None) -> None:
    db.add(MissionEvent(mission_id=mission.id, event_type=event_type, actor=actor, note=note, latitude=latitude, longitude=longitude))


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent update conflicts with an active assignment") from exc


def _request_code(now: datetime, request_id: int, uniqueness_token: str) -> str:
    # The ID gives operators a sortable sequence; the short UUID component also
    # protects legacy SQLite tables that may reuse an ID after a deletion.
    return f"SOS-{now:%Y%m%d}-{request_id:06d}-{uniqueness_token[:12].upper()}"


def _apply_ai_autofill(request: RescueRequest, payload: RescueRequestCreate) -> list[str]:
    """Apply only high-confidence suggestions for fields omitted by reporter."""
    analysis = request.ai_analysis or {}
    if float(analysis.get("confidence") or 0) < AI_AUTOFILL_CONFIDENCE:
        return []

    applied: list[str] = []
    provided = payload.model_fields_set
    for field in AI_AUTOFILL_FIELDS:
        suggestion = analysis.get(field)
        if field not in provided and suggestion is not None:
            setattr(request, field, suggestion)
            applied.append(field)

    location = analysis.get("extracted_location") or {}
    location_text = location.get("raw_text")
    if "address" not in provided and location_text:
        request.address = location_text
        applied.append("address")

    risks = set(analysis.get("detected_risks") or [])
    for field, risk in (("has_disabled_person", "disabled_person"), ("has_pregnant_person", "pregnant_person")):
        if field not in provided and risk in risks:
            setattr(request, field, True)
            applied.append(field)
    return applied


def _structured_analysis(payload: RescueRequestCreate | RescueRequest) -> tuple[dict, dict]:
    """Describe explicit form data without invoking any AI provider."""
    risks: list[str] = []
    needs = ["rescue"]
    if payload.is_trapped:
        risks.append("trapped")
    if payload.water_level is not None and payload.water_level >= 1.5:
        risks.append("high_water")
    if payload.number_of_children:
        risks.append("children")
    if payload.number_of_elderly:
        risks.append("elderly")
    if payload.number_of_injured:
        risks.append("injury")
        needs.append("medical_support")
    if payload.has_disabled_person:
        risks.append("disabled_person")
    if payload.has_pregnant_person:
        risks.append("pregnant_person")

    missing = [] if payload.address else ["exact_location"]
    if payload.water_level is None:
        missing.append("water_level")
    water_text = f"{payload.water_level:g} mét" if payload.water_level is not None else "chưa xác định"
    summary = (
        f"Biểu mẫu xác nhận {payload.number_of_people} người cần hỗ trợ, "
        f"gồm {payload.number_of_children} trẻ em; mực nước {water_text}."
    )
    analysis = {
        "summary": summary,
        "normalized_message": payload.message,
        "extracted_location": {
            "raw_text": payload.address,
            "province": None,
            "district": None,
            "commune": None,
            "village": None,
        },
        "number_of_people": payload.number_of_people,
        "number_of_children": payload.number_of_children,
        "number_of_elderly": payload.number_of_elderly,
        "number_of_injured": payload.number_of_injured,
        "is_trapped": payload.is_trapped,
        "water_level": payload.water_level,
        "needs": needs,
        "detected_risks": risks,
        "missing_information": missing,
        "confidence": 1.0,
        "explanation": "Dữ liệu do người báo nhập trực tiếp; Amazon Bedrock không được gọi cho luồng biểu mẫu.",
    }
    metadata = {
        "provider": "rule_based",
        "requested_provider": "none",
        "model_id": "priority-engine-v1",
        "latency_ms": 0.0,
        "analyzed_at": utc_now().isoformat(),
        "confidence": 1.0,
        "ai_invoked": False,
        "bedrock_succeeded": False,
        "fallback_used": False,
        "error_code": None,
        "auto_applied_fields": [],
    }
    return analysis, metadata


def _apply_demo_geocoding(request: RescueRequest, auto_applied_fields: list[str]) -> None:
    if request.latitude is not None or request.longitude is not None:
        return
    suggestion = suggest_demo_coordinates(request.address)
    if not suggestion:
        return
    request.latitude = suggestion.latitude
    request.longitude = suggestion.longitude
    auto_applied_fields.extend(["latitude", "longitude"])
    request.ai_metadata["geocoding"] = {
        "provider": "demo_gazetteer",
        "area_code": suggestion.area_code,
        "reference": suggestion.reference,
        "confidence": suggestion.confidence,
        "is_production_geocoder": False,
    }


def create_rescue_request(db: Session, payload: RescueRequestCreate) -> RescueRequest:
    """Create with a temporary UUID, then derive the human code from DB identity.

    The temporary value permits a single flush without nullable request_code;
    DB ids make the final code collision-free across deletions, re-seeding and
    concurrent submissions.
    """
    received_at = as_utc(payload.received_at or utc_now())
    for _ in range(3):
        now = utc_now()
        uniqueness_token = uuid4().hex[:12]
        request = RescueRequest(
            request_code=f"PENDING-{uniqueness_token}",
            **payload.model_dump(
                mode="json",
                exclude={"note", "received_at", "external_reference", "client_submission_id", "is_simulated", "raw_payload", "number_of_adults"},
            ),
            external_reference=payload.external_reference,
            client_submission_id=payload.client_submission_id,
            received_at=received_at,
            synced_at=now,
            is_simulated=payload.is_simulated,
            raw_payload=payload.raw_payload,
            created_at=received_at,
            updated_at=now,
            priority_calculated_at=now,
        )
        if payload.intake_mode == IntakeMode.STRUCTURED:
            request.ai_analysis, request.ai_metadata = _structured_analysis(payload)
            auto_applied_fields: list[str] = []
        else:
            request.ai_analysis, request.ai_metadata = analyze_with_fallback(request.message)
            auto_applied_fields = _apply_ai_autofill(request, payload)
            request.ai_metadata["auto_applied_fields"] = auto_applied_fields
        request.ai_metadata["intake_mode"] = payload.intake_mode.value
        _apply_demo_geocoding(request, auto_applied_fields)
        request.ai_metadata["auto_applied_fields"] = auto_applied_fields
        request.ai_fallback_used = bool(request.ai_metadata["fallback_used"])
        _apply_priority(request, now)
        db.add(request)
        try:
            db.flush()
            request.request_code = _request_code(now, request.id, uniqueness_token)
            note = payload.note
            if auto_applied_fields:
                suffix = f"AI extracted text-only fields: {', '.join(auto_applied_fields)}"
                note = f"{note}; {suffix}" if note else suffix
            _record_history(db, request, None, request.status, "reporter", note)
            db.commit()
        except IntegrityError:
            # Collision is extremely unlikely, but this also handles an old
            # SQLite table that reuses IDs after a delete.
            db.rollback()
            continue
        db.refresh(request)
        return request
    raise HTTPException(status_code=409, detail="Could not allocate a unique request code after retries")


def update_rescue_request(db: Session, request_id: int, payload: RescueRequestUpdate, changed_by: str = "admin") -> RescueRequest:
    request = db.get(RescueRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Rescue request not found")

    values = payload.model_dump(exclude_unset=True, exclude={"note", "status"})
    changed_priority_inputs = bool(PRIORITY_INPUT_FIELDS.intersection(values))
    for key, value in values.items():
        setattr(request, key, value)

    if payload.status is not None:
        # Verification is the only admin-side status action.  Assignment and
        # mission progress must go through their dedicated transactions.
        if payload.status != RequestStatus.VERIFIED.value:
            raise HTTPException(status_code=409, detail="Use assignment or mission status endpoints to advance this request")
        transition_request(db, request, payload.status, changed_by, payload.note, commit=False)

    if changed_priority_inputs:
        now = utc_now()
        if request.intake_mode == IntakeMode.STRUCTURED.value:
            request.ai_analysis, request.ai_metadata = _structured_analysis(request)
        else:
            request.ai_analysis, request.ai_metadata = analyze_with_fallback(request.message)
        request.ai_metadata["intake_mode"] = request.intake_mode
        request.ai_fallback_used = bool(request.ai_metadata["fallback_used"])
        _apply_priority(request, now)
        _record_history(
            db,
            request,
            request.status,
            request.status,
            changed_by,
            "Priority recalculated after request data update",
        )
    _commit(db)
    db.refresh(request)
    return request


def reanalyze_request(db: Session, request_id: int, changed_by: str = "admin") -> RescueRequest:
    """Refresh suggestions only; user-entered and verified fields are never overwritten."""
    request = db.get(RescueRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Rescue request not found")
    if request.intake_mode == IntakeMode.STRUCTURED.value:
        request.ai_analysis, request.ai_metadata = _structured_analysis(request)
        audit_note = "Rule-based analysis recalculated; Bedrock was not invoked for structured intake"
    else:
        request.ai_analysis, request.ai_metadata = analyze_with_fallback(request.message)
        audit_note = "AI analysis re-run; suggestions kept separate from reporter data"
    request.ai_metadata["intake_mode"] = request.intake_mode
    request.ai_fallback_used = bool(request.ai_metadata["fallback_used"])
    _record_history(db, request, request.status, request.status, changed_by, audit_note)
    _commit(db)
    db.refresh(request)
    return request


def transition_request(
    db: Session,
    request: RescueRequest,
    new_status: str,
    changed_by: str,
    note: str | None = None,
    *,
    commit: bool = True,
) -> None:
    allowed = REQUEST_TRANSITIONS.get(request.status, set())
    if new_status not in allowed:
        raise HTTPException(status_code=409, detail=f"Invalid request transition: {request.status} -> {new_status}")
    old_status = request.status
    request.status = new_status
    _record_history(db, request, old_status, new_status, changed_by, note)
    if commit:
        _commit(db)


def assign_request(db: Session, request_id: int, team_id: int, note: str | None = None) -> RescueMission:
    # Row locks make the application checks safe on PostgreSQL.  The two partial
    # unique indexes are a second line of defense on both supported databases.
    request = db.scalar(select(RescueRequest).where(RescueRequest.id == request_id).with_for_update())
    if not request:
        raise HTTPException(status_code=404, detail="Rescue request not found")
    team = db.scalar(select(RescueTeam).where(RescueTeam.id == team_id).with_for_update())
    if not team:
        raise HTTPException(status_code=404, detail="Rescue team not found")
    if request.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="Cannot assign a completed or failed request")
    if request.status != RequestStatus.VERIFIED.value:
        raise HTTPException(status_code=409, detail="Request must be VERIFIED before assignment")
    if team.status == TeamStatus.OFFLINE.value:
        raise HTTPException(status_code=409, detail="Cannot assign an offline team")
    if team.status == TeamStatus.BUSY.value or db.scalar(
        select(RescueMission.id).where(RescueMission.team_id == team.id, RescueMission.status.in_(ACTIVE_MISSION_STATUSES)).limit(1)
    ):
        raise HTTPException(status_code=409, detail="Cannot assign a team with an active mission")
    if db.scalar(
        select(RescueMission.id).where(RescueMission.request_id == request.id, RescueMission.status.in_(ACTIVE_MISSION_STATUSES)).limit(1)
    ):
        raise HTTPException(status_code=409, detail="Request already has an active mission")

    transition_request(db, request, RequestStatus.ASSIGNED.value, "admin", note, commit=False)
    request.assigned_team_id = team.id
    team.status = TeamStatus.BUSY.value
    team.active_mission_count += 1
    mission = RescueMission(request_id=request.id, team_id=team.id, status=MissionStatus.ASSIGNED.value, notes=note)
    db.add(mission)
    db.flush()
    _record_mission_event(db, mission, "ASSIGNED", "admin", note)
    _commit(db)
    return db.scalar(
        select(RescueMission)
        .options(joinedload(RescueMission.request).joinedload(RescueRequest.assigned_team), joinedload(RescueMission.team))
        .where(RescueMission.id == mission.id)
    )


def update_mission_status(db: Session, mission_id: int, status: str, note: str | None = None, latitude: float | None = None, longitude: float | None = None) -> RescueMission:
    mission = db.scalar(
        select(RescueMission)
        .options(joinedload(RescueMission.request), joinedload(RescueMission.team))
        .where(RescueMission.id == mission_id)
        # PostgreSQL rejects FOR UPDATE over nullable joinedload targets; lock
        # only the mission row while retaining the related request/team reads.
        .with_for_update(of=RescueMission)
    )
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if status not in {item.value for item in MissionStatus}:
        raise HTTPException(status_code=400, detail="Invalid mission status")
    if status not in MISSION_TRANSITIONS[mission.status]:
        raise HTTPException(status_code=409, detail=f"Invalid mission transition: {mission.status} -> {status}")
    if status not in REQUEST_TRANSITIONS[mission.request.status]:
        raise HTTPException(status_code=409, detail="Mission and request state are out of sync")

    now = utc_now()
    mission.status = status
    mission.notes = "\n".join(filter(None, [mission.notes, note]))
    if status == MissionStatus.ACCEPTED.value:
        mission.accepted_at = now
    if status == MissionStatus.ARRIVED.value:
        mission.arrived_at = now
    if status in TERMINAL_STATUSES:
        mission.completed_at = now
        mission.team.status = TeamStatus.AVAILABLE.value
        mission.team.active_mission_count = max(0, mission.team.active_mission_count - 1)
    event_names = {"ASSIGNED": "ASSIGNED", "ACCEPTED": "ACCEPTED", "MOVING": "DEPARTED", "ARRIVED": "ARRIVED", "BLOCKED": "ROUTE_BLOCKED", "NEED_REINFORCEMENT": "REINFORCEMENT_REQUESTED", "RESCUING": "RESCUING", "COMPLETED": "COMPLETED", "FAILED": "FAILED"}
    _record_mission_event(db, mission, event_names[status], "rescue_team", note, latitude, longitude)
    transition_request(db, mission.request, status, "rescue_team", note, commit=False)
    _commit(db)
    db.refresh(mission)
    return mission


def refresh_open_priorities(db: Session, now: datetime | None = None, refresh_interval_minutes: int = 5) -> int:
    """Refresh only stale, open requests; GET requests never create unbounded writes."""
    calculation_time = now or utc_now()
    open_requests = db.scalars(
        select(RescueRequest).where(RescueRequest.status.not_in(TERMINAL_STATUSES))
    ).all()
    refreshed = 0
    for request in open_requests:
        calculated_at = request.priority_calculated_at or request.created_at
        elapsed = (as_utc(calculation_time) - as_utc(calculated_at)).total_seconds()
        if elapsed < refresh_interval_minutes * 60:
            continue
        changed = _apply_priority(request, calculation_time)
        if changed:
            _record_history(
                db,
                request,
                request.status,
                request.status,
                "system",
                "Priority recalculated from waiting time",
            )
        refreshed += 1
    if refreshed:
        _commit(db)
    return refreshed
