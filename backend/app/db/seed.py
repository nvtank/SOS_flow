from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import RescueRequest, RescueStation, RescueTeam, TeamStatus
from app.schemas.rescue import RescueRequestCreate
from app.core.time import utc_now
from app.models.entities import RequestStatus
from app.services.rescue_service import create_rescue_request, transition_request


STATION_SEED = [
    # Fixed demo reference points. They are not claims about live government-team deployment.
    # TRL-01 uses the public administrative address; its coordinate is the published-map
    # centroid of Xã Trà Linh until the operator records a verified station GPS position.
    {"code": "TRL-01", "name": "Điểm trực demo — UBND Xã Trà Linh", "area_code": "TRA_LINH", "address": "Thôn 3, Xã Trà Linh, thành phố Đà Nẵng", "latitude": 15.023565, "longitude": 108.041263},
    {"code": "DNG-01", "name": "Điểm trực demo — PCCC & CNCH Đà Nẵng", "area_code": "DA_NANG", "address": "183 Phan Đăng Lưu, thành phố Đà Nẵng", "latitude": 16.035971, "longitude": 108.213402},
    {"code": "DNG-02", "name": "Điểm trực demo — Bệnh viện Đà Nẵng", "area_code": "DA_NANG", "address": "124 Hải Phòng, phường Thạch Thang, thành phố Đà Nẵng", "latitude": 16.072259, "longitude": 108.216008},
]

DEFAULT_TEAM_STATIONS = {
    "Đội Xuồng Cứu Hộ 01": "DNG-01",
    "Đội Y Tế Cơ Động 02": "DNG-02",
    "Đội Leo Dây 03": "TRL-01",
}


def ensure_rescue_stations(db: Session) -> dict[str, RescueStation]:
    stations: dict[str, RescueStation] = {}
    for values in STATION_SEED:
        station = db.scalar(select(RescueStation).where(RescueStation.code == values["code"]))
        if not station:
            station = RescueStation(**values, is_simulated=True, is_active=True)
            db.add(station)
        elif station.is_simulated:
            # Correct previously seeded demo coordinates on existing databases without
            # touching any real station an operator may have entered.
            for field, value in values.items():
                setattr(station, field, value)
            station.is_active = True
        stations[values["code"]] = station
    db.commit()
    for station in stations.values():
        db.refresh(station)
    return stations


def _station_for_team(team: RescueTeam, stations: dict[str, RescueStation]) -> RescueStation:
    latitude = team.current_latitude if team.current_latitude is not None else team.latitude
    # The two intentional map scopes are Trà Linh and Đà Nẵng only.
    if latitude is not None and latitude < 15.5:
        return stations["TRL-01"]
    return stations["DNG-01"]


def seed_database(db: Session) -> None:
    stations = ensure_rescue_stations(db)
    existing_teams = db.scalars(select(RescueTeam)).all()
    if existing_teams:
        changed = False
        for team in existing_teams:
            desired_station = stations.get(DEFAULT_TEAM_STATIONS.get(team.name, ""))
            if team.station_id is None or desired_station is not None:
                station = desired_station or _station_for_team(team, stations)
                if team.station_id != station.id:
                    team.station_id = station.id
                    changed = True
                # Seed/demo teams have no live tracking, so their displayed location
                # follows their corrected fixed reference point even after a reseed.
                for field, value in (("latitude", station.latitude), ("longitude", station.longitude), ("current_latitude", station.latitude), ("current_longitude", station.longitude)):
                    if getattr(team, field) != value:
                        setattr(team, field, value)
                        changed = True
        if changed:
            db.commit()
        return

    teams = [
        RescueTeam(name="Đội Xuồng Cứu Hộ 01", phone_number="0901000001", member_count=6, vehicle_type="Xuồng máy", station_id=stations["DNG-01"].id, latitude=stations["DNG-01"].latitude, longitude=stations["DNG-01"].longitude, current_latitude=stations["DNG-01"].latitude, current_longitude=stations["DNG-01"].longitude, capabilities=["flood_rescue", "medical"], equipment=["xuồng cứu hộ", "áo phao", "túi sơ cứu"], max_people_capacity=12, status=TeamStatus.AVAILABLE.value),
        RescueTeam(name="Đội Y Tế Cơ Động 02", phone_number="0901000002", member_count=4, vehicle_type="Xe cứu thương", station_id=stations["DNG-02"].id, latitude=stations["DNG-02"].latitude, longitude=stations["DNG-02"].longitude, current_latitude=stations["DNG-02"].latitude, current_longitude=stations["DNG-02"].longitude, capabilities=["medical"], equipment=["cáng", "oxy", "túi sơ cứu"], max_people_capacity=4, status=TeamStatus.BUSY.value),
        RescueTeam(name="Đội Leo Dây 03", phone_number="0901000003", member_count=5, vehicle_type="Xe bán tải", station_id=stations["DNG-02"].id, latitude=stations["DNG-02"].latitude, longitude=stations["DNG-02"].longitude, current_latitude=stations["DNG-02"].latitude, current_longitude=stations["DNG-02"].longitude, capabilities=["landslide"], equipment=["dây thừng", "mũ bảo hộ"], max_people_capacity=5, status=TeamStatus.OFFLINE.value),
    ]
    db.add_all(teams)
    db.commit()

    samples = [
        RescueRequestCreate(reporter_name="Nguyễn Văn An", phone_number="0912000001", message="Nhà tôi có 5 người, 2 trẻ em, nước đang lên rất nhanh, chúng tôi không ra được.", address="Đường Nguyễn Lương Bằng, Đà Nẵng", latitude=16.072, longitude=108.15, number_of_people=5, number_of_children=2, is_trapped=True, water_level=2.6),
        RescueRequestCreate(reporter_name="Trần Thị Bình", phone_number="0912000002", message="Cứu với, bà tôi bị thương, nước đã gần tới nóc nhà.", address="Phường Hòa Khánh", latitude=16.075, longitude=108.17, number_of_people=2, number_of_elderly=1, number_of_injured=1, water_level=2.4),
        RescueRequestCreate(reporter_name="Lê Văn Cường", phone_number="0912000003", message="Có 3 người đang mắc kẹt gần cầu, sóng điện thoại rất yếu.", address="Gần cầu Nam Ô", latitude=16.093, longitude=108.13, number_of_people=3, is_trapped=True, water_level=1.2),
        RescueRequestCreate(reporter_name="Phạm Minh Dũng", phone_number="0912000004", message="Nhà tôi bị ngập nhưng hiện tại mọi người vẫn an toàn.", address="Hòa Minh", latitude=16.065, longitude=108.18, number_of_people=4, water_level=0.4),
        RescueRequestCreate(reporter_name="Võ Thị Hoa", phone_number="0912000005", message="Sắp chết rồi, có người không thở được, nước cuốn rất mạnh.", address="Thôn ven sông Cu Đê", latitude=16.12, longitude=108.1, number_of_people=6, number_of_children=1, number_of_injured=2, has_pregnant_person=True, is_trapped=True, water_level=3.0),
        RescueRequestCreate(reporter_name="Hoàng Long", phone_number="0912000006", message="Nha toi bi ngap noc, co 2 nguoi gia, khong ra duoc.", address="Xã Hòa Liên", latitude=16.11, longitude=108.12, number_of_people=4, number_of_elderly=2, is_trapped=True, water_level=2.7),
        RescueRequestCreate(reporter_name="Mai Anh", phone_number="0912000007", message="Có 1 người cần hỗ trợ di chuyển do nước tràn vào nhà.", address=None, latitude=None, longitude=None, number_of_people=1, water_level=0.8),
        RescueRequestCreate(reporter_name="Đỗ Hạnh", phone_number="0912000008", message="Có 3 người đang mắc kẹt gần cầu, sóng điện thoại rất yếu.", address="Gần cầu Nam Ô, phía chợ", latitude=16.094, longitude=108.131, number_of_people=3, is_trapped=True, water_level=1.1),
        RescueRequestCreate(reporter_name="Bùi Sơn", phone_number="0912000009", message="Sạt lở sau nhà, 2 người già và một người khuyết tật đang ở trong nhà.", address="Hòa Sơn", latitude=16.08, longitude=108.05, number_of_people=3, number_of_elderly=2, has_disabled_person=True, water_level=0.2),
        RescueRequestCreate(reporter_name="Lý Nam", phone_number="0912000010", message="Cần nước uống và đưa trẻ em ra khỏi vùng ngập.", address="Khu dân cư số 5", latitude=16.052, longitude=108.21, number_of_people=7, number_of_children=3, water_level=1.0),
    ]
    created = []
    for sample in samples:
        request = create_rescue_request(db, sample)
        transition_request(db, request, RequestStatus.VERIFIED.value, "seed", "Seed request verified")
        created.append(request)

    # Spread creation times so waiting-time scoring and table sorting feel realistic.
    for index, request in enumerate(db.scalars(select(RescueRequest)).all()):
        request.created_at = utc_now() - timedelta(minutes=index * 7)
    db.commit()
