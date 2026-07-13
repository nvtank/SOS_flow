from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import Base
from app.models.entities import MissionEvent, MissionStatus, RequestStatus, RescueRequest, RescueStation, RescueTeam, TeamStatus
from app.schemas.rescue import RescueRequestCreate
from app.services import ai_analyzer, rescue_service
from app.services.ai_analyzer import BedrockEmergencyAnalyzer, EmergencyAnalysis
from app.services.dispatch_recommendation_service import recommend_teams
from app.services.priority_engine import PriorityEngine


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


@pytest.fixture()
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(rescue_service, "_engine", lambda: PriorityEngine(RULES_PATH))
    with Session(engine) as session:
        yield session


def tool_response(**overrides):
    payload = {
        "summary": "Có người mắc kẹt cần hỗ trợ.", "normalized_message": "co nguoi mac ket",
        "extracted_location": {"raw_text": "cầu Trà Linh", "province": None, "district": None, "commune": None, "village": None},
        "number_of_people": 3, "number_of_children": 1, "number_of_elderly": None, "number_of_injured": 1,
        "is_trapped": True, "water_level": 2.1, "needs": ["rescue"], "detected_risks": ["trapped", "injury"],
        "missing_information": [], "confidence": 0.88, "explanation": "Thông tin được trích xuất từ tin báo.",
    }
    payload.update(overrides)
    return {"output": {"message": {"content": [{"toolUse": {"name": "submit_emergency_analysis", "input": payload}}]}}}


def test_bedrock_structured_tool_output_is_validated():
    class Client:
        def converse(self, **kwargs):
            assert kwargs["toolConfig"]["toolChoice"]["tool"]["name"] == "submit_emergency_analysis"
            return tool_response()

    analyzer = BedrockEmergencyAnalyzer(Settings(ai_provider="bedrock", bedrock_model_id="test-model"), Client())
    result = analyzer.analyze("Có 3 người mắc kẹt")

    assert isinstance(result, EmergencyAnalysis)
    assert result.number_of_people == 3


@pytest.mark.parametrize("failure", [ValueError("invalid json"), TimeoutError("too slow")])
def test_bedrock_failures_fall_back_without_losing_analysis(monkeypatch, failure):
    class FailingAnalyzer:
        provider_name = "bedrock"
        def analyze(self, message):
            raise failure

    settings = Settings(ai_provider="bedrock", bedrock_model_id="test-model", ai_fallback_enabled=True)
    monkeypatch.setattr(ai_analyzer, "get_emergency_analyzer", lambda _: FailingAnalyzer())
    analysis, metadata = ai_analyzer.analyze_with_fallback("Nước lên, 2 người mắc kẹt", settings)

    assert metadata["fallback_used"] is True
    assert metadata["error_code"] in {"INVALID_STRUCTURED_OUTPUT", "TIMEOUT"}
    assert EmergencyAnalysis.model_validate(analysis).summary


def test_reanalysis_keeps_reporter_data_and_writes_audit(db, monkeypatch):
    monkeypatch.setattr(rescue_service, "analyze_with_fallback", lambda _: ({"number_of_people": 1, "summary": "gợi ý", "confidence": 0.4}, {"fallback_used": False}))
    request = rescue_service.create_rescue_request(db, RescueRequestCreate(message="Có 5 người cần giúp", number_of_people=5))
    refreshed = rescue_service.reanalyze_request(db, request.id)

    assert refreshed.number_of_people == 5
    assert refreshed.ai_analysis["number_of_people"] == 1
    assert any("AI analysis re-run" in (item.note or "") for item in refreshed.status_history)


def test_text_only_report_uses_high_confidence_ai_suggestions_for_priority(db, monkeypatch):
    analysis = tool_response()["output"]["message"]["content"][0]["toolUse"]["input"]
    monkeypatch.setattr(rescue_service, "analyze_with_fallback", lambda _: (analysis, {"fallback_used": False, "provider": "bedrock"}))

    request = rescue_service.create_rescue_request(db, RescueRequestCreate(message="Có 3 người, 1 trẻ em và 1 người bị thương mắc kẹt."))

    assert request.number_of_people == 3
    assert request.number_of_children == 1
    assert request.number_of_injured == 1
    assert request.is_trapped is True
    assert request.water_level == 2.1
    assert set(request.ai_metadata["auto_applied_fields"]) >= {"number_of_people", "number_of_children", "number_of_injured", "is_trapped", "water_level"}
    assert request.priority_level in {"HIGH", "CRITICAL"}


def test_recommendation_prefers_capable_nearby_available_team_without_assigning(db):
    request = rescue_service.create_rescue_request(db, RescueRequestCreate(message="Nước dâng, có người bị thương", latitude=16.05, longitude=108.20, number_of_people=4, number_of_injured=1, water_level=2.2))
    nearby = RescueTeam(name="Xuồng gần", status=TeamStatus.AVAILABLE.value, current_latitude=16.051, current_longitude=108.201, vehicle_type="Xuồng", capabilities=["flood_rescue", "medical"], equipment=["xuồng", "túi sơ cứu"], max_people_capacity=8)
    far = RescueTeam(name="Xuồng xa", status=TeamStatus.AVAILABLE.value, current_latitude=16.3, current_longitude=108.4, vehicle_type="Xuồng", capabilities=["flood_rescue", "medical"], max_people_capacity=8)
    offline = RescueTeam(name="Đội offline", status=TeamStatus.OFFLINE.value, current_latitude=16.05, current_longitude=108.20, capabilities=["flood_rescue", "medical"])
    db.add_all([nearby, far, offline]); db.commit()

    recommendations = recommend_teams(db, request.id)

    assert recommendations[0]["team_id"] == nearby.id
    assert offline.id not in {item["team_id"] for item in recommendations}
    assert db.get(RescueRequest, request.id).assigned_team_id is None


def test_recommendation_uses_fixed_rescue_station_when_live_gps_is_missing(db):
    station = RescueStation(code="DNG-TEST", name="Trạm test Đà Nẵng", area_code="DA_NANG", latitude=16.050, longitude=108.200)
    request = rescue_service.create_rescue_request(db, RescueRequestCreate(message="Nước dâng rất nhanh", latitude=16.052, longitude=108.202, number_of_people=2, is_trapped=True))
    team = RescueTeam(name="Đội từ trạm", status=TeamStatus.AVAILABLE.value, station=station, capabilities=["flood_rescue"], max_people_capacity=6)
    db.add_all([station, team]); db.commit()

    recommendation = recommend_teams(db, request.id)[0]

    assert recommendation["team_id"] == team.id
    assert recommendation["estimated_distance_km"] is not None
    assert recommendation["estimated_distance_km"] < 1
    assert any("đường thẳng" in reason for reason in recommendation["reasons"])


def test_blocked_reinforcement_lifecycle_records_mission_events(db):
    request = rescue_service.create_rescue_request(db, RescueRequestCreate(message="Cần cứu hộ", latitude=16.05, longitude=108.2))
    rescue_service.transition_request(db, request, RequestStatus.VERIFIED.value, "admin")
    team = RescueTeam(name="Team", status=TeamStatus.AVAILABLE.value)
    db.add(team); db.commit()
    mission = rescue_service.assign_request(db, request.id, team.id)

    for status in (MissionStatus.ACCEPTED.value, MissionStatus.MOVING.value, MissionStatus.BLOCKED.value, MissionStatus.MOVING.value, MissionStatus.ARRIVED.value, MissionStatus.NEED_REINFORCEMENT.value, MissionStatus.RESCUING.value, MissionStatus.COMPLETED.value):
        mission = rescue_service.update_mission_status(db, mission.id, status, note=status)

    event_types = set(db.scalars(select(MissionEvent.event_type).where(MissionEvent.mission_id == mission.id)).all())
    assert {"ROUTE_BLOCKED", "REINFORCEMENT_REQUESTED", "COMPLETED"}.issubset(event_types)
    assert mission.request.status == RequestStatus.COMPLETED.value
    assert mission.team.status == TeamStatus.AVAILABLE.value
    assert mission.team.active_mission_count == 0


def test_invalid_bedrock_structure_becomes_fallback(monkeypatch):
    class InvalidClient:
        def converse(self, **kwargs):
            return {"output": {"message": {"content": [{"text": "not a tool result"}]}}}

    settings = Settings(ai_provider="bedrock", bedrock_model_id="test-model", ai_fallback_enabled=True)
    analyzer = BedrockEmergencyAnalyzer(settings, InvalidClient())
    monkeypatch.setattr(ai_analyzer, "get_emergency_analyzer", lambda _: analyzer)
    _, metadata = ai_analyzer.analyze_with_fallback("Cứu tôi", settings)

    assert metadata["fallback_used"] is True
    assert metadata["error_code"] == "INVALID_STRUCTURED_OUTPUT"
