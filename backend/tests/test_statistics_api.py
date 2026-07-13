from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.core.config import get_settings
from app.db.session import Base, get_db
from app.main import app, settings
from app.schemas.rescue import RescueRequestCreate
from app.services import rescue_service
from app.services.intake_service import intake_rescue_request
from app.services.priority_engine import PriorityEngine


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


def test_statistics_uses_operational_aggregates(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    monkeypatch.setattr(settings, "seed_on_startup", False)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(get_settings(), "demo_mode", True)

    for payload in (
        RescueRequestCreate(message="5 người mắc kẹt, nước lên nhanh", source="CALL_112", latitude=16.0, longitude=108.0, number_of_people=5, is_trapped=True, water_level=2.5),
        RescueRequestCreate(message="Tin SMS thiếu vị trí", source="SMS", number_of_people=1),
    ):
        intake_rescue_request(session, payload, simulated=True)

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        response = client.get("/api/admin/statistics")
    app.dependency_overrides.clear()
    session.close()

    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] == 2
    assert body["missing_location_count"] == 1
    assert {item["label"] for item in body["requests_by_source"]} == {"CALL_112", "SMS"}
    assert body["requests_over_time_minutes"]
    assert "average_waiting_minutes" in body
