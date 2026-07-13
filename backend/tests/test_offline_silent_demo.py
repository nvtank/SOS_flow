from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.time import as_utc, utc_now
from app.db.session import Base
from app.models.entities import IntakeSource, RescueRequest, SilentZone, SilentZoneVerificationStatus
from app.schemas.rescue import RescueRequestCreate
from app.services import rescue_service
from app.services.demo_scenario_service import inject_all, start_scenario
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
    zone = SilentZone(name="Vùng thử", latitude=22.5, longitude=104.4, radius_meters=1_000, hazard_active=True, last_report_at=utc_now() - timedelta(minutes=35), silence_threshold_minutes=20)
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
    assert zones and zones[0]["name"] == "Khe Nậm Chảy"
