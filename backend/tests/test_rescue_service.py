from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import Base
from app.models.entities import MissionStatus, RequestStatus, RescueMission, RescueRequest, RescueTeam, TeamStatus
from app.schemas.rescue import RescueRequestCreate, RescueRequestUpdate
from app.services import rescue_service
from app.services.priority_engine import PriorityEngine, PriorityInput


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    with Session(engine) as session:
        yield session


def make_request(db: Session, **values) -> RescueRequest:
    payload = RescueRequestCreate(message="Nước đang lên nhanh, chúng tôi mắc kẹt", **values)
    return rescue_service.create_rescue_request(db, payload)


def verify(db: Session, request: RescueRequest) -> None:
    rescue_service.update_rescue_request(db, request.id, RescueRequestUpdate(status=RequestStatus.VERIFIED.value))


def test_request_code_uses_database_identity_not_record_count(db):
    first = make_request(db)
    first_code = first.request_code
    db.delete(first)
    db.commit()

    second = make_request(db)

    assert first_code.startswith("SOS-")
    assert second.request_code.startswith("SOS-")
    assert second.request_code != first_code
    assert second.request_code.split("-")[2] == f"{second.id:06d}"


def test_update_recalculates_priority_and_writes_audit_history(db):
    request = make_request(db, number_of_people=1, water_level=0.1)
    original_score = request.priority_score

    updated = rescue_service.update_rescue_request(
        db,
        request.id,
        RescueRequestUpdate(number_of_people=9, number_of_injured=2, water_level=3.0),
    )

    assert updated.priority_score > original_score
    assert updated.ai_analysis
    history = list(updated.status_history)
    assert any(entry.note == "Priority recalculated after request data update" for entry in history)


def test_aging_is_deterministic_with_injected_time():
    engine = PriorityEngine(RULES_PATH)
    created_at = utc_now() - timedelta(minutes=120)
    initial = engine.calculate(PriorityInput(message="Cần hỗ trợ", created_at=created_at), now=created_at)
    aged = engine.calculate(PriorityInput(message="Cần hỗ trợ", created_at=created_at), now=created_at + timedelta(minutes=120))

    assert aged["priority_score"] > initial["priority_score"]
    assert any("Đã chờ 120 phút" in reason for reason in aged["reasons"])


def test_request_and_mission_transitions_cannot_skip_or_go_backwards(db):
    request = make_request(db)
    with pytest.raises(HTTPException, match="Invalid request transition"):
        rescue_service.transition_request(db, request, RequestStatus.MOVING.value, "admin")

    verify(db, request)
    team = RescueTeam(name="Team 1")
    db.add(team)
    db.commit()
    mission = rescue_service.assign_request(db, request.id, team.id)

    with pytest.raises(HTTPException, match="Invalid mission transition"):
        rescue_service.update_mission_status(db, mission.id, MissionStatus.ARRIVED.value)

    for status in (MissionStatus.ACCEPTED.value, MissionStatus.MOVING.value, MissionStatus.ARRIVED.value, MissionStatus.RESCUING.value):
        mission = rescue_service.update_mission_status(db, mission.id, status)
    mission = rescue_service.update_mission_status(db, mission.id, MissionStatus.COMPLETED.value)

    assert mission.request.status == RequestStatus.COMPLETED.value
    with pytest.raises(HTTPException, match="Invalid mission transition"):
        rescue_service.update_mission_status(db, mission.id, MissionStatus.MOVING.value)


def test_assignment_prevents_double_active_missions_and_restores_team_after_terminal_status(db):
    first = make_request(db)
    second = make_request(db)
    verify(db, first)
    verify(db, second)
    team = RescueTeam(name="Team 1")
    other_team = RescueTeam(name="Team 2")
    db.add_all([team, other_team])
    db.commit()

    mission = rescue_service.assign_request(db, first.id, team.id)
    with pytest.raises(HTTPException, match="VERIFIED|active mission"):
        rescue_service.assign_request(db, first.id, other_team.id)
    with pytest.raises(HTTPException, match="active mission"):
        rescue_service.assign_request(db, second.id, team.id)

    for status in (MissionStatus.ACCEPTED.value, MissionStatus.MOVING.value, MissionStatus.ARRIVED.value, MissionStatus.RESCUING.value, MissionStatus.FAILED.value):
        mission = rescue_service.update_mission_status(db, mission.id, status)
    assert mission.team.status == TeamStatus.AVAILABLE.value


def test_assignment_rolls_back_request_and_team_when_commit_fails(db, monkeypatch):
    request = make_request(db)
    verify(db, request)
    team = RescueTeam(name="Team 1")
    db.add(team)
    db.commit()

    def fail_commit():
        raise IntegrityError("insert", {}, Exception("forced failure"))

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(HTTPException, match="Concurrent update"):
        rescue_service.assign_request(db, request.id, team.id)

    db.expire_all()
    assert db.get(RescueRequest, request.id).status == RequestStatus.VERIFIED.value
    assert db.get(RescueTeam, team.id).status == TeamStatus.AVAILABLE.value
    assert db.scalar(select(RescueMission).where(RescueMission.request_id == request.id)) is None
