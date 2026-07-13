"""Transparent, approval-only rescue team recommendations."""

from math import asin, cos, radians, sin, sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import RescueRequest, RescueTeam, TeamStatus


def _distance_km(request: RescueRequest, team: RescueTeam) -> float | None:
    latitude = team.current_latitude if team.current_latitude is not None else team.latitude
    longitude = team.current_longitude if team.current_longitude is not None else team.longitude
    if None in (request.latitude, request.longitude, latitude, longitude): return None
    lat1, lon1, lat2, lon2 = map(radians, (request.latitude, request.longitude, latitude, longitude))
    value = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(6371 * 2 * asin(sqrt(value)), 1)


def _required_capabilities(request: RescueRequest) -> set[str]:
    risks = set((request.ai_analysis or {}).get("detected_risks", []))
    requirements: set[str] = set()
    if request.is_trapped or "trapped" in risks or (request.water_level or 0) >= 1: requirements.add("flood_rescue")
    if request.number_of_injured or "injury" in risks: requirements.add("medical")
    if "landslide" in risks or "sạt lở" in request.message.lower(): requirements.add("landslide")
    return requirements


def recommend_teams(db: Session, request_id: int, limit: int = 3) -> list[dict]:
    request = db.get(RescueRequest, request_id)
    if not request: raise ValueError("Rescue request not found")
    requirements = _required_capabilities(request); recommendations = []
    for team in db.scalars(select(RescueTeam).where(RescueTeam.status == TeamStatus.AVAILABLE.value)).all():
        reasons = ["Đội đang sẵn sàng"]; warnings = []; score = 45
        distance = _distance_km(request, team)
        if distance is None: warnings.append("Thiếu vị trí đội hoặc sự cố; không thể tính khoảng cách")
        else:
            score += max(0, 25 - int(distance * 2)); reasons.append(f"Cách sự cố khoảng {distance:.1f} km theo đường thẳng")
        capabilities = set(team.capabilities or [])
        matched = requirements & capabilities
        if matched: score += len(matched) * 12; reasons.append("Có năng lực: " + ", ".join(sorted(matched)))
        if requirements - capabilities: warnings.append("Thiếu năng lực được gợi ý: " + ", ".join(sorted(requirements - capabilities)))
        if team.max_people_capacity is not None:
            if team.max_people_capacity >= request.number_of_people: score += 10; reasons.append(f"Sức chứa {team.max_people_capacity} người phù hợp")
            else: score -= 20; warnings.append(f"Sức chứa {team.max_people_capacity} thấp hơn {request.number_of_people} người")
        if team.vehicle_type: reasons.append(f"Phương tiện: {team.vehicle_type}")
        if team.active_mission_count: score -= team.active_mission_count * 20; warnings.append("Đội đang có nhiệm vụ active")
        recommendations.append({"team_id": team.id, "team_name": team.name, "recommendation_score": max(0, min(100, score)), "estimated_distance_km": distance, "vehicle_type": team.vehicle_type, "capabilities": team.capabilities or [], "reasons": reasons, "warnings": warnings})
    return sorted(recommendations, key=lambda item: (-item["recommendation_score"], item["estimated_distance_km"] is None, item["estimated_distance_km"] or 9999))[:limit]
