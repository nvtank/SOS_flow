from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import RescueRequest, RescueTeam, TeamStatus
from app.schemas.rescue import RescueRequestCreate
from app.services.rescue_service import create_rescue_request


def seed_database(db: Session) -> None:
    if db.scalar(select(RescueTeam).limit(1)):
        return

    teams = [
        RescueTeam(name="Đội Xuồng Cứu Hộ 01", phone_number="0901000001", member_count=6, vehicle_type="Xuồng máy", latitude=16.0471, longitude=108.2068, status=TeamStatus.AVAILABLE.value),
        RescueTeam(name="Đội Y Tế Cơ Động 02", phone_number="0901000002", member_count=4, vehicle_type="Xe cứu thương", latitude=16.0602, longitude=108.223, status=TeamStatus.BUSY.value),
        RescueTeam(name="Đội Leo Dây 03", phone_number="0901000003", member_count=5, vehicle_type="Xe bán tải", latitude=16.031, longitude=108.19, status=TeamStatus.OFFLINE.value),
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
        created.append(create_rescue_request(db, sample))

    # Spread creation times so waiting-time scoring and table sorting feel realistic.
    for index, request in enumerate(db.scalars(select(RescueRequest)).all()):
        request.created_at = datetime.utcnow() - timedelta(minutes=index * 7)
    db.commit()
