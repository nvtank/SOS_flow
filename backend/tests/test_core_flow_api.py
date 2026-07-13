"""API-level end-to-end core rescue flow (frontend/browser independent)."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.db.session import Base, get_db
from app.main import app, settings
from app.models.entities import RescueTeam, TeamStatus
from app.services import rescue_service
from app.services.priority_engine import PriorityEngine


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


def test_report_to_completed_mission_is_visible_in_dashboard(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    monkeypatch.setattr(settings, "seed_on_startup", False)
    monkeypatch.setattr(main, "engine", engine)
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    team = RescueTeam(name="E2E đội xuồng", status=TeamStatus.AVAILABLE.value, capabilities=["flood_rescue"], max_people_capacity=10)
    db.add(team); db.commit()

    with TestClient(app) as client:
        created = client.post("/api/rescue-requests", json={"message": "Có 4 người mắc kẹt, nước lên nhanh", "number_of_people": 4, "is_trapped": True, "water_level": 2.1, "client_submission_id": "e2e-core-flow"})
        assert created.status_code == 200
        request_id = created.json()["id"]
        assert client.patch(f"/api/admin/rescue-requests/{request_id}", json={"status": "VERIFIED"}).status_code == 200
        assigned = client.post(f"/api/admin/rescue-requests/{request_id}/assign", json={"team_id": team.id})
        assert assigned.status_code == 200
        mission_id = assigned.json()["id"]
        for status in ("ACCEPTED", "MOVING", "ARRIVED", "RESCUING", "COMPLETED"):
            assert client.patch(f"/api/missions/{mission_id}/status", json={"status": status}).status_code == 200
        assert client.get("/api/admin/statistics").json()["completed"] == 1

    app.dependency_overrides.clear(); db.close()
