from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import router
from app.db.session import Base, get_db
from app import main
from app.main import app, settings
from app.schemas.rescue import RescueRequestCreate
from app.services import rescue_service
from app.services.priority_engine import PriorityEngine


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    monkeypatch.setattr(settings, "seed_on_startup", False)
    monkeypatch.setattr(main, "engine", engine)

    def override_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, session
    app.dependency_overrides.clear()
    session.close()


def test_requests_are_paginated_and_filterable(client):
    test_client, session = client
    for index in range(3):
        rescue_service.create_rescue_request(
            session,
            RescueRequestCreate(message=f"Yêu cầu cứu hộ số {index}", source="SMS" if index < 2 else "WEB"),
        )

    response = test_client.get("/api/admin/rescue-requests?page=1&page_size=1&source=SMS&sort_by=created_at&sort_order=asc")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["created_at"].endswith("Z")
