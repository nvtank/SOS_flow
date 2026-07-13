from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.time import as_utc, utc_now
from app.db.session import Base
from app.models.entities import DuplicateState, IntakeSource, MissionStatus, RequestStatus, RescueRequest, RescueTeam, SilentZone, SilentZoneVerificationStatus
from app.schemas.rescue import RescueRequestCreate
from app.services import rescue_service
from app.services.demo_scenario_service import inject_all, inject_next, pause_scenario, reset_scenario, set_scenario_speed, start_scenario
from app.services.intake_service import intake_rescue_request
from app.services.priority_engine import PriorityEngine
from app.services.silent_zone_service import list_silent_zones, note_report, update_verification


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    with Session(engine) as session:
        yield session


def test_offline_sync_idempotency_keeps_original_time_and_server_sync_time(db):
    created_local = utc_now() - timedelta(minutes=20)
    payload = RescueRequestCreate(message="Ghi nhận khi mất mạng, có 2 người cần hỗ trợ", source=IntakeSource.OFFLINE_SYNC, client_submission_id="device-unique-1", received_at=created_local)
    first, duplicate = intake_rescue_request(db, payload)
    again, duplicate_again = intake_rescue_request(db, payload)

    assert duplicate is False
    assert duplicate_again is True
    assert first.id == again.id
    assert first.source == IntakeSource.OFFLINE_SYNC.value
    assert as_utc(first.received_at) == created_local
    assert as_utc(first.synced_at) >= as_utc(first.received_at)


def test_silent_zone_is_only_verification_signal_and_has_audit(db):
    zone = SilentZone(name="Vùng thử", latitude=15.02, longitude=108.04, radius_meters=1_000, hazard_active=True, last_report_at=utc_now() - timedelta(minutes=35), silence_threshold_minutes=20)
    db.add(zone); db.commit()

    alert = list_silent_zones(db, only_alerts=True)
    assert alert[0]["reason"].startswith("Khu vực có hazard")
    updated = update_verification(db, zone.id, SilentZoneVerificationStatus.VERIFYING.value, "Gọi cán bộ xã")
    assert updated.verification_status == SilentZoneVerificationStatus.VERIFYING.value
    assert len(updated.history) == 1
    note_report(db, zone.latitude, zone.longitude)
    db.commit()
    assert list_silent_zones(db, only_alerts=True) == []


def test_tra_linh_scenario_inject_all_creates_real_reports_missions_and_silent_zone(db):
    start_scenario(db, speed=2)
    result = inject_all(db)

    assert result["complete"] is True
    assert len(result["injected"]) == 12
    assert db.query(RescueRequest).filter(RescueRequest.source == IntakeSource.OFFLINE_SYNC.value).count() == 1
    zones = list_silent_zones(db, only_alerts=True)
    assert zones and zones[0]["name"] == "Khu vực cần xác minh Trà Linh"


def test_demo_playback_speed_does_not_reset_and_manual_step_works_while_paused(db):
    started = start_scenario(db, speed=1)
    assert started["paused"] is False
    first = inject_next(db)
    assert first["next_event"] == 1

    pause_scenario(db, True)
    changed = set_scenario_speed(db, 5)
    assert changed["next_event"] == 1
    assert changed["speed"] == 5
    assert changed["paused"] is True

    # "Inject next" is a manual stepping control, so it remains usable while
    # automatic playback is paused.
    second = inject_next(db)
    assert second["next_event"] == 2
    assert second["paused"] is True

    reset = reset_scenario(db)
    assert reset["next_event"] == 0
    assert reset["paused"] is True


def test_demo_reset_clears_stale_duplicate_warning_from_real_report(db):
    real, _ = intake_rescue_request(
        db,
        RescueRequestCreate(
            message="112 báo 6 người, có 2 trẻ em bị mắc kẹt gần Thôn 3, nước cuốn mạnh.",
            source="WEB", address="Thôn 3, Xã Trà Linh, thành phố Đà Nẵng",
            latitude=15.0232, longitude=108.0409, number_of_people=6,
            number_of_children=2, is_trapped=True, water_level=2.8,
        ),
    )
    start_scenario(db)
    inject_next(db)
    db.refresh(real)
    assert real.duplicate_state == DuplicateState.POSSIBLE_DUPLICATE.value

    reset_scenario(db)
    db.refresh(real)
    assert real.duplicate_state == DuplicateState.NOT_DUPLICATE.value


def test_demo_reset_preserves_team_referenced_by_real_mission_audit(db):
    start_scenario(db)
    team = db.query(RescueTeam).filter(RescueTeam.name == "Demo Đội Dự bị Trà Linh A").one()
    real, _ = intake_rescue_request(
        db,
        RescueRequestCreate(message="2 người mắc kẹt cần xuồng", number_of_people=2, is_trapped=True),
    )
    rescue_service.transition_request(db, real, RequestStatus.VERIFIED.value, "test")
    mission = rescue_service.assign_request(db, real.id, team.id)
    for status in (MissionStatus.ACCEPTED.value, MissionStatus.MOVING.value, MissionStatus.ARRIVED.value, MissionStatus.RESCUING.value, MissionStatus.COMPLETED.value):
        mission = rescue_service.update_mission_status(db, mission.id, status)

    reset_scenario(db)

    assert db.get(RescueTeam, team.id) is not None
    assert db.get(type(mission), mission.id).team_id == team.id
