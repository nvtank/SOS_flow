#!/usr/bin/env python3
"""Send demo-only multi-source reports to SOSFlow's real intake API.

This is a simulator. It does not connect to a real SMS, Zalo, phone, or 112
provider. The API must start with DEMO_MODE=true and a matching DEMO_TOKEN.
"""

import argparse
import json
from datetime import UTC, datetime, timedelta
from time import sleep
from urllib.request import Request, urlopen


def reports() -> list[dict]:
    received = datetime.now(UTC)
    base = [
        {"source": "CALL_112", "message": "112 báo có 5 người, 2 trẻ em mắc kẹt gần cầu Trà Linh, nước lên nhanh.", "address": "Cầu Trà Linh", "latitude": 16.0710, "longitude": 108.1510, "number_of_people": 5, "number_of_children": 2, "is_trapped": True, "water_level": 2.2},
        {"source": "SMS", "message": "Cứu với, nhà gần cầu Trà Linh có 5 nguoi va 2 tre em, nuoc dang len, khong ra duoc.", "address": "Gần cầu Trà Linh", "latitude": 16.0718, "longitude": 108.1515, "number_of_people": 5, "number_of_children": 2, "is_trapped": True, "water_level": 2.1},
        {"source": "LOCAL_OFFICER", "message": "Cán bộ phường xác nhận một hộ sát cầu Trà Linh bị cô lập, có trẻ nhỏ.", "address": "Cầu Trà Linh", "latitude": 16.0702, "longitude": 108.1508, "number_of_people": 5, "number_of_children": 2, "is_trapped": True, "water_level": 2.3},
        {"source": "PHONE", "message": "Có người bị thương ở đường Nguyễn Lương Bằng, cần xe y tế ngay.", "address": "Đường Nguyễn Lương Bằng", "latitude": 16.073, "longitude": 108.151, "number_of_people": 2, "number_of_injured": 1},
        {"source": "WEB", "message": "Nhà tôi ngập nhẹ, mọi người vẫn an toàn, cần theo dõi.", "address": "Hòa Minh", "latitude": 16.065, "longitude": 108.18, "number_of_people": 3, "water_level": 0.3},
        {"source": "SOCIAL_MEDIA", "message": "Sạt lở sau nhà, có 2 người già và một người khuyết tật.", "address": "Hòa Sơn", "latitude": 16.08, "longitude": 108.05, "number_of_people": 3, "number_of_elderly": 2, "has_disabled_person": True},
        {"source": "SMS", "message": "Ko ro dia chi, nuoc vao nha nhanh, co em be.", "number_of_people": 2, "number_of_children": 1, "water_level": 1.1},
        {"source": "ZALO", "message": "Có 1 người không thở được, nước cuốn rất mạnh, xin cứu gấp.", "address": "Ven sông Cu Đê", "latitude": 16.12, "longitude": 108.1, "number_of_people": 1, "number_of_injured": 1, "water_level": 3.0},
        {"source": "OFFLINE_SYNC", "message": "Báo cáo offline đồng bộ muộn: 4 người cần nước uống tại khu dân cư số 5.", "address": "Khu dân cư số 5", "latitude": 16.052, "longitude": 108.21, "number_of_people": 4, "received_at": (received - timedelta(minutes=45)).isoformat()},
        {"source": "PHONE", "message": "Có 3 người mắc kẹt ở khu Nam Ô, sóng điện thoại yếu.", "address": "Gần cầu Nam Ô", "latitude": 16.093, "longitude": 108.13, "number_of_people": 3, "is_trapped": True, "water_level": 1.2},
        {"source": "WEB", "message": "Gia đình an toàn nhưng cần hướng dẫn di chuyển khi nước rút.", "address": "Hòa Liên", "latitude": 16.11, "longitude": 108.12, "number_of_people": 4},
        {"source": "LOCAL_OFFICER", "message": "Điểm tham chiếu What3words cần xác minh tọa độ trước khi điều phối.", "address": "///slipped.awkward.scarecrow", "number_of_people": 1, "raw_payload": {"what3words_url": "https://what3words.com/slipped.awkward.scarecrow"}},
    ]
    for index, report in enumerate(base, start=1):
        report["client_submission_id"] = f"disaster-demo-20260713-{index:02d}"
        report["external_reference"] = f"SIM-{report['source']}-{index:03d}"
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject 12 simulated SOS reports through SOSFlow's demo API")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--token", default="sosflow-demo")
    parser.add_argument("--delay-ms", type=int, default=120)
    args = parser.parse_args()

    endpoint = args.api_url.rstrip("/") + "/api/demo/intake"
    for report in reports():
        request = Request(
            endpoint,
            data=json.dumps(report).encode(),
            headers={"Content-Type": "application/json", "X-Demo-Token": args.token},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:  # nosec: local demo URL set intentionally by operator
            body = json.loads(response.read())
        print(f"{body['request_code']} <- {report['source']}: {body['duplicate_state']}")
        if args.delay_ms:
            sleep(args.delay_ms / 1000)


if __name__ == "__main__":
    main()
