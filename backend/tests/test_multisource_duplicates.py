from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import Base
from app.models.entities import DuplicateState, RescueRequest
from app.schemas.rescue import DemoIntakeBatch, RescueRequestCreate
from app.services import rescue_service
from app.services.duplicate_service import score_duplicate
from app.services.intake_service import intake_rescue_request
from app.services.duplicate_service import decide_duplicate, merge_duplicate_report
from app.api.demo_routes import demo_intake_batch
from app.services.priority_engine import PriorityEngine


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    with Session(engine) as session:
        yield session


def payload(message: str, **values) -> RescueRequestCreate:
    return RescueRequestCreate(message=message, **values)


def test_nearby_similar_reports_create_explainable_candidate_without_auto_merge(db):
    first, _ = intake_rescue_request(
        db,
        payload(
            "Có 5 người và 2 trẻ em mắc kẹt gần cầu Trà Linh, nước lên nhanh.",
            source="CALL_112", address="Cầu Trà Linh", latitude=16.0710, longitude=108.1510,
            number_of_people=5, number_of_children=2, is_trapped=True,
        ),
        simulated=True,
    )
    second, _ = intake_rescue_request(
        db,
        payload(
            "Cứu với, 5 nguoi va 2 tre em mac ket gan cau Tra Linh, nuoc dang len.",
            source="SMS", address="Gần cầu Trà Linh", latitude=16.0718, longitude=108.1515,
            number_of_people=5, number_of_children=2, is_trapped=True,
        ),
        simulated=True,
    )

    candidate = second.duplicate_candidates[0]
    assert candidate.duplicate_score >= 0.55
    assert candidate.confidence_level in {"MEDIUM", "HIGH"}
    assert any("cách nhau" in reason or "Nội dung giống" in reason for reason in candidate.reasons)
    assert second.canonical_request_id is None
    assert candidate.status == DuplicateState.POSSIBLE_DUPLICATE.value


def test_different_incidents_have_low_score(db):
    first, _ = intake_rescue_request(db, payload("Sạt lở ở Hòa Sơn, cần hỗ trợ người già.", address="Hòa Sơn", latitude=16.08, longitude=108.05), simulated=True)
    second, _ = intake_rescue_request(db, payload("Nhà bị cháy ở ven sông Cu Đê, cần cứu thương.", address="Ven sông Cu Đê", latitude=16.12, longitude=108.1), simulated=True)

    result = score_duplicate(first, second)
    assert result["duplicate_score"] < 0.55
    assert not second.duplicate_candidates


def test_idempotency_returns_the_original_report(db):
    data = payload("Tin từ SMS cần hỗ trợ.", source="SMS", client_submission_id="phone-retry-001", external_reference="sms-001")
    first, reused_first = intake_rescue_request(db, data, simulated=True)
    retry, reused_retry = intake_rescue_request(db, data, simulated=True)

    assert reused_first is False
    assert reused_retry is True
    assert retry.id == first.id
    assert db.scalar(select(func.count(RescueRequest.id))) == 1


def test_confirm_and_merge_preserve_the_original_report_and_audit(db):
    canonical, _ = intake_rescue_request(db, payload("Ba người mắc kẹt ở cầu Trà Linh.", address="Cầu Trà Linh", latitude=16.071, longitude=108.151, is_trapped=True), simulated=True)
    report, _ = intake_rescue_request(db, payload("3 nguoi mac ket gan cau Tra Linh.", address="Gần cầu Trà Linh", latitude=16.0712, longitude=108.1512, is_trapped=True), simulated=True)
    candidate = report.duplicate_candidates[0]

    decide_duplicate(db, report.id, candidate.id, confirmed=True, note="Cùng một hộ dân")
    merged = merge_duplicate_report(db, report.id, canonical.id, candidate.id, note="Gộp để điều phối một incident")

    assert merged.id == report.id
    assert merged.canonical_request_id == canonical.id
    assert db.get(RescueRequest, report.id) is not None
    assert any("merged into canonical" in (entry.note or "").lower() for entry in report.status_history)


def test_demo_batch_keeps_the_requested_sources(db):
    batch = DemoIntakeBatch(
        reports=[
            payload("Tin từ 112 cần xác minh.", source="CALL_112", client_submission_id="batch-1"),
            payload("Tin đồng bộ offline muộn.", source="OFFLINE_SYNC", client_submission_id="batch-2", received_at=utc_now() - timedelta(minutes=20)),
        ]
    )

    accepted = demo_intake_batch(batch, db)

    assert [request.source for request in accepted] == ["CALL_112", "OFFLINE_SYNC"]
    assert all(request.is_simulated for request in accepted)
