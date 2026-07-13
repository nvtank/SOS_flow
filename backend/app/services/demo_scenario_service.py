"""Deterministic, demo-only Trà Linh scenario driven through domain services."""

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.entities import DemoScenarioState, MissionStatus, RequestStatus, RescueRequest, RescueStation, RescueTeam, SilentZone, SilentZoneHistory, TeamStatus
from app.schemas.rescue import RescueRequestCreate
from app.services.intake_service import intake_rescue_request
from app.services.rescue_service import assign_request, transition_request, update_mission_status


SCENARIO_KEY = "tra-linh-flood-landslide"


def _report(external_reference: str, source: str, message: str, **values) -> RescueRequestCreate:
    return RescueRequestCreate(
        source=source, external_reference=external_reference, client_submission_id=f"demo-{external_reference}",
        message=message, reporter_name=values.pop("reporter_name", "Demo Trà Linh"), is_simulated=True, **values,
    )


REPORT_EVENTS = [
    ("112 critical", _report("trl-112", "CALL_112", "112 báo 6 người, có 2 trẻ em bị mắc kẹt gần Thôn 3, nước cuốn mạnh.", address="Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0232, longitude=108.0409, number_of_people=6, number_of_children=2, is_trapped=True, number_of_injured=1, water_level=2.8)),
    ("SMS sai chính tả", _report("trl-sms", "SMS", "cuu voi nha e ngap gan noc co 3 nguoi o thon 3 tra linh", address="Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0236, longitude=108.0411, number_of_people=3, is_trapped=True, water_level=2.4)),
    ("Web report", _report("trl-web", "WEB", "Nhà gần Thôn 3, Xã Trà Linh có ba người, nước lên nhanh, không thể ra ngoài.", address="Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0234, longitude=108.0410, number_of_people=3, is_trapped=True, water_level=2.2)),
    ("Zalo simulator", _report("trl-zalo", "ZALO", "Zalo giả lập: 3 người mắc kẹt ở Thôn 3, Xã Trà Linh, nước rất cao.", address="Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0235, longitude=108.0410, number_of_people=3, is_trapped=True, water_level=2.3)),
    ("Cán bộ xã", _report("trl-officer", "LOCAL_OFFICER", "Cán bộ xã xác nhận hộ dân gần Thôn 3, Xã Trà Linh có người mắc kẹt.", address="Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0233, longitude=108.0412, number_of_people=3, is_trapped=True, water_level=2.1)),
    ("Critical trẻ em chưa giao đội", _report("trl-children", "WEB", "Có 4 trẻ em và 2 người lớn mắc kẹt gần Nhà văn hóa Konpin, một người bị thương nặng.", address="Nhà văn hóa Konpin, Thôn 2, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0350, longitude=108.0550, number_of_people=6, number_of_children=4, number_of_injured=1, is_trapped=True, water_level=2.9)),
    ("Tin thiếu tọa độ", _report("trl-missing-location", "PHONE", "Nhà bị sạt lở, 2 người già cần hỗ trợ nhưng sóng rất yếu.", address=None, number_of_people=2, number_of_elderly=2)),
    ("Offline sync muộn", _report("trl-offline-late", "OFFLINE_SYNC", "Cán bộ ghi nhận offline: 2 người cần sơ cứu sau lũ.", address="Thôn 2, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0280, longitude=108.0480, number_of_people=2, number_of_injured=1, received_at=utc_now() - timedelta(minutes=47))),
    ("Tin xã hội bình thường", _report("trl-social", "SOCIAL_MEDIA", "Người dân khu chợ tạm thời an toàn, cần nước uống.", address="Nhà văn hóa Konpin, Thôn 2, Xã Trà Linh, thành phố Đà Nẵng", latitude=15.0348, longitude=108.0547, number_of_people=5, water_level=0.4)),
]


def _state(db: Session) -> DemoScenarioState:
    state = db.scalar(select(DemoScenarioState).where(DemoScenarioState.scenario_key == SCENARIO_KEY))
    if not state:
        state = DemoScenarioState(scenario_key=SCENARIO_KEY)
        db.add(state); db.commit(); db.refresh(state)
    return state


def _scenario_team(db: Session, name: str, capabilities: list[str]) -> RescueTeam:
    team = db.scalar(select(RescueTeam).where(RescueTeam.name == name))
    if not team:
        station = db.scalar(select(RescueStation).where(RescueStation.code == "TRL-01"))
        if not station:
            from app.db.seed import ensure_rescue_stations
            station = ensure_rescue_stations(db)["TRL-01"]
        team = RescueTeam(name=name, status=TeamStatus.AVAILABLE.value, vehicle_type="Xuồng cứu hộ", capabilities=capabilities, equipment=["xuồng cứu hộ", "áo phao", "túi sơ cứu"], max_people_capacity=10, station_id=station.id, latitude=station.latitude, longitude=station.longitude, current_latitude=station.latitude, current_longitude=station.longitude)
        db.add(team); db.commit(); db.refresh(team)
    return team


def _request(db: Session, external_reference: str) -> RescueRequest:
    request = db.scalar(select(RescueRequest).where(RescueRequest.external_reference == external_reference))
    if not request:
        raise HTTPException(status_code=409, detail="Inject prerequisite report first")
    return request


def _verify(db: Session, request: RescueRequest) -> None:
    if request.status == RequestStatus.PENDING_VERIFICATION.value:
        transition_request(db, request, RequestStatus.VERIFIED.value, "demo", "Demo coordinator verification")


def _blocked_mission(db: Session) -> list[int]:
    request = _request(db, "trl-112"); _verify(db, request)
    team = _scenario_team(db, "Demo Đội Xuồng Trà Linh", ["flood_rescue", "medical"])
    mission = assign_request(db, request.id, team.id, "Demo assignment")
    for status in (MissionStatus.ACCEPTED.value, MissionStatus.MOVING.value, MissionStatus.BLOCKED.value):
        mission = update_mission_status(db, mission.id, status, "Tuyến đường bị sạt lở trong demo")
    return [request.id]


def _reinforcement_mission(db: Session) -> list[int]:
    request = _request(db, "trl-children"); _verify(db, request)
    team = _scenario_team(db, "Demo Đội Y tế Trà Linh", ["flood_rescue", "medical"])
    mission = assign_request(db, request.id, team.id, "Demo assignment")
    for status in (MissionStatus.ACCEPTED.value, MissionStatus.MOVING.value, MissionStatus.ARRIVED.value, MissionStatus.NEED_REINFORCEMENT.value):
        mission = update_mission_status(db, mission.id, status, "Cần thêm xuồng và nhân lực y tế")
    return [request.id]


def _silent_zone(db: Session) -> list[int]:
    zone = db.scalar(select(SilentZone).where(SilentZone.scenario_key == SCENARIO_KEY, SilentZone.name == "Khu vực cần xác minh Trà Linh"))
    if not zone:
        zone = SilentZone(name="Khu vực cần xác minh Trà Linh", scenario_key=SCENARIO_KEY, latitude=15.0600, longitude=108.0900, radius_meters=1_200, hazard_active=True, last_report_at=utc_now() - timedelta(minutes=50), silence_threshold_minutes=20)
        db.add(zone); db.flush()
        db.add(SilentZoneHistory(zone_id=zone.id, old_status=None, new_status=zone.verification_status, actor="demo", note="Khu vực cần xác minh trong scenario Trà Linh"))
        db.commit()
    return []


def _inject_event(db: Session, index: int) -> tuple[str, list[int]]:
    if index < len(REPORT_EVENTS):
        label, payload = REPORT_EVENTS[index]
        request, _ = intake_rescue_request(db, payload, simulated=True)
        return label, [request.id]
    if index == len(REPORT_EVENTS):
        return "Mission BLOCKED", _blocked_mission(db)
    if index == len(REPORT_EVENTS) + 1:
        return "Mission NEED_REINFORCEMENT", _reinforcement_mission(db)
    if index == len(REPORT_EVENTS) + 2:
        return "Vùng im lặng cần xác minh tại Trà Linh", _silent_zone(db)
    raise HTTPException(status_code=409, detail="Scenario is already complete")


def reset_scenario(db: Session) -> dict:
    """Delete only simulator-owned records and deterministic demo support data."""
    for request in db.scalars(select(RescueRequest).where(RescueRequest.is_simulated.is_(True))).all():
        db.delete(request)
    for zone in db.scalars(select(SilentZone).where(SilentZone.scenario_key == SCENARIO_KEY)).all():
        db.delete(zone)
    db.flush()
    for team in db.scalars(select(RescueTeam).where(RescueTeam.name.like("Demo Đội %"))).all():
        db.delete(team)
    state = _state(db); state.next_event = 0; state.paused = False; state.speed = 1
    db.commit()
    return scenario_status(db)


def start_scenario(db: Session, speed: int = 1) -> dict:
    reset_scenario(db)
    # Keep three available options after the two scripted missions occupy their
    # own teams, so Request Detail can demonstrate a top-three recommendation.
    _scenario_team(db, "Demo Đội Dự bị Trà Linh A", ["flood_rescue", "medical"])
    _scenario_team(db, "Demo Đội Dự bị Trà Linh B", ["flood_rescue"])
    state = _state(db); state.speed = speed; db.commit()
    return scenario_status(db)


def scenario_status(db: Session) -> dict:
    state = _state(db)
    return {"scenario": SCENARIO_KEY, "next_event": state.next_event, "total_events": len(REPORT_EVENTS) + 3, "paused": state.paused, "speed": state.speed, "complete": state.next_event >= len(REPORT_EVENTS) + 3}


def pause_scenario(db: Session, paused: bool) -> dict:
    state = _state(db); state.paused = paused; db.commit()
    return scenario_status(db)


def inject_next(db: Session) -> dict:
    state = _state(db)
    if state.paused:
        raise HTTPException(status_code=409, detail="Scenario is paused")
    label, request_ids = _inject_event(db, state.next_event)
    state.next_event += 1; db.commit()
    return {**scenario_status(db), "event": label, "request_ids": request_ids}


def inject_all(db: Session) -> dict:
    state = _state(db)
    if state.paused:
        raise HTTPException(status_code=409, detail="Scenario is paused")
    injected = []
    while state.next_event < len(REPORT_EVENTS) + 3:
        label, request_ids = _inject_event(db, state.next_event)
        state.next_event += 1
        injected.append({"event": label, "request_ids": request_ids})
        db.commit()
    return {**scenario_status(db), "injected": injected}
