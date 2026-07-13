"""
EmergencyPrioritizer — So sanh va xep hang uu tien cuu ho.

Ket hop 3 tang:
  1. Rule-based scoring: tinh diem nhanh, deterministic
  2. Distance tiebreaker: khi score gan nhau, case xa tram cuu ho hon duoc uu tien
  3. LLM (Bedrock): so sanh ngu canh, giai thich ly do bang ngon ngu tu nhien
"""

import json
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from .schemas import AIAnalysis, PrioritizedCase, PriorityReport, RescueStation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rescue stations — cac tram cuu ho co dinh (demo Da Nang / Tra Linh)
# ---------------------------------------------------------------------------
DEFAULT_RESCUE_STATIONS: list[RescueStation] = [
    RescueStation(
        name="UBND Xa Tra Linh",
        latitude=15.023565,
        longitude=108.041263,
        station_type="admin",
    ),
    RescueStation(
        name="PCCC & CNCH Da Nang",
        latitude=16.035971,
        longitude=108.213402,
        station_type="rescue",
    ),
    RescueStation(
        name="Benh vien Da Nang",
        latitude=16.072259,
        longitude=108.216008,
        station_type="medical",
    ),
]


# ---------------------------------------------------------------------------
# Haversine distance (pure Python, khong can thu vien ngoai)
# ---------------------------------------------------------------------------
_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tinh khoang cach great-circle giua 2 diem (km).
    Dung cong thuc Haversine — du chinh xac cho cuu ho.
    """
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_KM * c


def find_nearest_station(
    lat: float,
    lon: float,
    stations: list[RescueStation] | None = None,
) -> tuple[RescueStation, float]:
    """
    Tim tram cuu ho gan nhat.

    Returns:
        (station, distance_km)
    """
    if stations is None:
        stations = DEFAULT_RESCUE_STATIONS

    best_station = stations[0]
    best_dist = haversine_km(lat, lon, stations[0].latitude, stations[0].longitude)

    for station in stations[1:]:
        dist = haversine_km(lat, lon, station.latitude, station.longitude)
        if dist < best_dist:
            best_dist = dist
            best_station = station

    return best_station, round(best_dist, 2)


# ---------------------------------------------------------------------------
# Rule-based scoring
# ---------------------------------------------------------------------------
def _score_level(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def rule_based_score(analysis: AIAnalysis) -> float:
    """
    Tinh diem uu tien dua tren rule cung (0-100).

    Trong so:
      - Trapped:        +30
      - Injured:        +5 moi nguoi (max +25)
      - Children:       +4 moi tre (max +16)
      - Elderly:        +4 moi nguoi gia (max +16)
      - Water level:    +3 moi 0.5m (max +18)
      - People:         +1 moi nguoi (max +10)
      - Risks:          +3 moi risk (max +15)
      - Needs:          +2 moi need (max +10)
    """
    score = 0.0

    if analysis.is_trapped:
        score += 30

    injured = analysis.number_of_injured or 0
    score += min(injured * 5, 25)

    children = analysis.number_of_children or 0
    score += min(children * 4, 16)

    elderly = analysis.number_of_elderly or 0
    score += min(elderly * 4, 16)

    if analysis.water_level is not None and analysis.water_level > 0:
        score += min(analysis.water_level / 0.5 * 3, 18)

    people = analysis.number_of_people or 0
    score += min(people * 1, 10)

    score += min(len(analysis.detected_risks) * 3, 15)
    score += min(len(analysis.needs) * 2, 10)

    return min(100.0, round(score, 1))


def distance_bonus(distance_km: float) -> float:
    """
    Tinh diem bonus dua tren khoang cach toi tram cuu ho.
    Case xa hon can duoc uu tien hon (cuu ho mat nhieu thoi gian hon).

    Scale: 0-8 diem
      - 0 km    -> 0 diem
      - 5 km    -> 2 diem
      - 20 km   -> 4 diem
      - 50 km   -> 6 diem
      - 100+ km -> 8 diem
    """
    if distance_km <= 0:
        return 0.0
    # Logarithmic scaling: bonus = 2 * ln(1 + distance/5), cap at 8
    bonus = 2.0 * math.log(1.0 + distance_km / 5.0)
    return min(8.0, round(bonus, 1))


def rule_based_reasoning(
    analysis: AIAnalysis,
    score: float,
    station_name: Optional[str] = None,
    dist_km: Optional[float] = None,
) -> str:
    """Tao giai thich rule-based."""
    parts: list[str] = []

    if analysis.is_trapped:
        parts.append("nan nhan dang mac ket (yeu to khan cap nhat)")

    injured = analysis.number_of_injured or 0
    if injured > 0:
        parts.append(f"{injured} nguoi bi thuong")

    children = analysis.number_of_children or 0
    if children > 0:
        parts.append(f"co {children} tre em (doi tuong de bi ton thuong)")

    elderly = analysis.number_of_elderly or 0
    if elderly > 0:
        parts.append(f"co {elderly} nguoi gia")

    if analysis.water_level and analysis.water_level > 0:
        parts.append(f"muc nuoc {analysis.water_level}m")

    people = analysis.number_of_people or 0
    if people > 0:
        parts.append(f"tong cong {people} nguoi")

    if analysis.detected_risks:
        parts.append(f"rui ro: {', '.join(analysis.detected_risks)}")

    if analysis.needs:
        parts.append(f"can: {', '.join(analysis.needs)}")

    if dist_km is not None and station_name:
        parts.append(f"cach tram '{station_name}' {dist_km:.1f}km")

    if not parts:
        parts.append("khong co thong tin chi tiet")

    level = _score_level(score)
    return f"[{level} - {score} diem] " + "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Coordinate extraction from text
# ---------------------------------------------------------------------------
_COORD_PATTERN = re.compile(
    r"@\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)"
)

_LATLON_PATTERN = re.compile(
    r"(?:toa do|tọa độ|vi tri|vị trí|gps)[:\s]*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)",
    re.IGNORECASE,
)


def extract_coordinates(text: str) -> tuple[Optional[float], Optional[float], str]:
    """
    Extract toa do tu text. Ho tro:
      - "@15.023,108.041" (cuoi bao cao)
      - "toa do 15.023, 108.041"
      - "vi tri: 15.023, 108.041"

    Returns:
        (latitude, longitude, clean_text_without_coord_marker)
    """
    # Pattern 1: @lat,lon
    match = _COORD_PATTERN.search(text)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        clean = text[:match.start()].strip()
        return lat, lon, clean

    # Pattern 2: "toa do lat, lon"
    match = _LATLON_PATTERN.search(text)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        return lat, lon, text

    return None, None, text


# ---------------------------------------------------------------------------
# Prioritizer class
# ---------------------------------------------------------------------------
class EmergencyPrioritizer:
    """
    So sanh nhieu case va xep hang uu tien.

    mode:
      - "rule":    chi dung rule-based scoring + distance
      - "bedrock": rule-based + distance + LLM giai thich (mac dinh)
    """

    def __init__(
        self,
        mode: str = "bedrock",
        stations: list[RescueStation] | None = None,
    ) -> None:
        self.mode = mode.lower()
        self.stations = stations or DEFAULT_RESCUE_STATIONS
        self._client = None
        self._prompt_path = (
            Path(__file__).parent / "prompts" / "priority_system.txt"
        )

    def _get_bedrock_client(self) -> Any:
        """Lazy init Bedrock client."""
        if self._client is not None:
            return self._client

        try:
            import boto3
            from dotenv import load_dotenv

            env_path = Path(__file__).resolve().parent / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=False)

            region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
            kwargs: dict[str, Any] = {}
            if region:
                kwargs["region_name"] = region
            self._client = boto3.client("bedrock-runtime", **kwargs)
            return self._client
        except Exception as exc:
            logger.warning("Cannot init Bedrock client: %s", exc)
            return None

    async def prioritize(
        self,
        cases: dict[str, AIAnalysis],
    ) -> PriorityReport:
        """
        Xep hang uu tien cho nhieu case.

        Args:
            cases: dict mapping case_id -> AIAnalysis
                   (AIAnalysis.extracted_location co the co lat/lon)

        Returns:
            PriorityReport voi cases da sap xep theo uu tien giam dan
        """
        if not cases:
            return PriorityReport(
                cases=[],
                overall_summary="Khong co case nao de so sanh.",
            )

        # Buoc 1: Rule-based scoring + distance (with auto-geocoding)
        scored: list[PrioritizedCase] = []
        for case_id, analysis in cases.items():
            base_score = rule_based_score(analysis)

            # Auto-geocode if we have address text but no coordinates
            lat = analysis.extracted_location.latitude
            lon = analysis.extracted_location.longitude

            if lat is None or lon is None:
                lat, lon = await self._try_geocode(analysis, case_id)

            # Distance calculation
            station_name: Optional[str] = None
            dist_km: Optional[float] = None
            dist_extra = 0.0

            if lat is not None and lon is not None:
                station, dist = find_nearest_station(lat, lon, self.stations)
                station_name = station.name
                dist_km = dist
                dist_extra = distance_bonus(dist)
                logger.info(
                    "Case %s: lat=%.4f lon=%.4f -> nearest=%s dist=%.1fkm bonus=+%.1f",
                    case_id, lat, lon, station.name, dist, dist_extra,
                )

            final_score = min(100.0, round(base_score + dist_extra, 1))
            level = _score_level(final_score)
            reasoning = rule_based_reasoning(analysis, final_score, station_name, dist_km)

            scored.append(PrioritizedCase(
                case_id=case_id,
                priority_score=final_score,
                priority_level=level,
                reasoning=reasoning,
                nearest_station=station_name,
                distance_km=dist_km,
                original_analysis=analysis,
            ))

        # Sap xep: score giam dan, neu bang nhau thi xa hon truoc
        scored.sort(
            key=lambda c: (c.priority_score, c.distance_km or 0),
            reverse=True,
        )

        # Buoc 2: LLM comparison (neu mode=bedrock va co >= 2 case)
        if self.mode == "bedrock" and len(scored) >= 2:
            llm_report = await self._llm_compare(scored)
            if llm_report is not None:
                return llm_report

        # Fallback: rule-based summary
        order = " > ".join(
            f"{c.case_id}({c.priority_level})"
            for c in scored
        )
        summary = f"Thu tu uu tien cuu ho: {order}"

        return PriorityReport(cases=scored, overall_summary=summary)

    # ------------------------------------------------------------------
    # Auto-geocoding
    # ------------------------------------------------------------------
    async def _try_geocode(
        self,
        analysis: AIAnalysis,
        case_id: str,
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Thu geocode dia chi tu analysis.extracted_location hoac normalized_message.
        Neu thanh cong, update lat/lon vao analysis.
        """
        from .geocoder import geocode_location_text

        # Thu 1: raw_text tu extracted_location
        raw_text = analysis.extracted_location.raw_text
        if raw_text:
            result = await geocode_location_text(raw_text)
            if result:
                lat, lon, display = result
                analysis.extracted_location.latitude = lat
                analysis.extracted_location.longitude = lon
                logger.info(
                    "Case %s: geocoded '%s' -> (%.6f, %.6f)",
                    case_id, raw_text, lat, lon,
                )
                return lat, lon

        # Thu 2: normalized_message (toan bo bao cao)
        # Chi thu khi message ngan (< 100 chars) de tranh noise
        msg = analysis.normalized_message
        if msg and len(msg) < 100:
            result = await geocode_location_text(msg)
            if result:
                lat, lon, display = result
                analysis.extracted_location.latitude = lat
                analysis.extracted_location.longitude = lon
                logger.info(
                    "Case %s: geocoded message -> (%.6f, %.6f)",
                    case_id, lat, lon,
                )
                return lat, lon

        return None, None

    # ------------------------------------------------------------------
    # LLM comparison
    # ------------------------------------------------------------------
    async def _llm_compare(
        self,
        scored_cases: list[PrioritizedCase],
    ) -> PriorityReport | None:
        """Goi Bedrock de so sanh va giai thich uu tien."""
        client = self._get_bedrock_client()
        if client is None:
            return None

        invoke_target = (
            os.getenv("BEDROCK_INFERENCE_PROFILE_ARN")
            or os.getenv("BEDROCK_INFERENCE_PROFILE_ID")
            or os.getenv("BEDROCK_MODEL_ID", "")
        )
        if not invoke_target:
            return None

        max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "2048"))

        # Build user prompt — include distance info
        cases_json: list[dict[str, Any]] = []
        for case in scored_cases:
            case_data: dict[str, Any] = {
                "case_id": case.case_id,
                "rule_score": case.priority_score,
                "summary": case.original_analysis.summary,
                "number_of_people": case.original_analysis.number_of_people,
                "number_of_children": case.original_analysis.number_of_children,
                "number_of_elderly": case.original_analysis.number_of_elderly,
                "number_of_injured": case.original_analysis.number_of_injured,
                "is_trapped": case.original_analysis.is_trapped,
                "water_level": case.original_analysis.water_level,
                "needs": case.original_analysis.needs,
                "detected_risks": case.original_analysis.detected_risks,
                "location": case.original_analysis.extracted_location.raw_text,
            }
            if case.nearest_station and case.distance_km is not None:
                case_data["nearest_rescue_station"] = case.nearest_station
                case_data["distance_to_station_km"] = case.distance_km
            cases_json.append(case_data)

        user_content = (
            f"Compare the following {len(cases_json)} emergency cases "
            f"and rank by rescue priority.\n"
            f"Consider distance to rescue station as a tiebreaker "
            f"when severity scores are similar (farther = harder to reach = higher priority).\n\n"
            f"{json.dumps(cases_json, indent=2, ensure_ascii=False)}\n\n"
            f"Return only valid JSON matching the schema."
        )

        system_prompt = self._prompt_path.read_text(encoding="utf-8")

        try:
            logger.info("Calling Bedrock for priority comparison (%d cases)...", len(cases_json))
            t0 = time.monotonic()
            response = client.converse(
                modelId=invoke_target,
                system=[{"text": system_prompt}],
                messages=[
                    {"role": "user", "content": [{"text": user_content}]},
                ],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": 0.1,
                },
            )
            elapsed = time.monotonic() - t0

            output_msg = response.get("output", {}).get("message", {})
            content_blocks = output_msg.get("content", [])
            text = "\n".join(
                b["text"] for b in content_blocks
                if isinstance(b, dict) and "text" in b
            )
            logger.info("Priority comparison OK - %.2fs, %d chars", elapsed, len(text))

            parsed = self._extract_json(text)
            return self._build_report(parsed, scored_cases)

        except Exception as exc:
            logger.warning("LLM priority comparison failed: %s", exc)
            return None

    def _extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if md_match:
            try:
                return json.loads(md_match.group(1))
            except json.JSONDecodeError:
                pass

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Cannot parse priority JSON: {text[:200]}")

    def _build_report(
        self,
        llm_data: dict[str, Any],
        scored_cases: list[PrioritizedCase],
    ) -> PriorityReport:
        """Merge LLM ranking with original data (preserve distance info)."""
        # Map case_id -> original scored case (with distance info)
        case_map = {c.case_id: c for c in scored_cases}

        ranked = llm_data.get("ranked_cases", [])
        result_cases: list[PrioritizedCase] = []

        for item in ranked:
            case_id = item.get("case_id", "")
            original_case = case_map.get(case_id)
            if original_case is None:
                continue

            score = float(item.get("priority_score", 0))
            level = item.get("priority_level", _score_level(score))
            reasoning = item.get("reasoning", "No reasoning provided.")

            # Append distance info to reasoning if available
            if original_case.distance_km is not None and original_case.nearest_station:
                reasoning += (
                    f" [Distance: {original_case.distance_km:.1f}km"
                    f" to {original_case.nearest_station}]"
                )

            result_cases.append(PrioritizedCase(
                case_id=case_id,
                priority_score=score,
                priority_level=level,
                reasoning=reasoning,
                nearest_station=original_case.nearest_station,
                distance_km=original_case.distance_km,
                original_analysis=original_case.original_analysis,
            ))

        # Neu LLM bo sot case nao, them lai
        seen_ids = {c.case_id for c in result_cases}
        for case in scored_cases:
            if case.case_id not in seen_ids:
                result_cases.append(case)

        result_cases.sort(key=lambda c: c.priority_score, reverse=True)

        summary = llm_data.get("overall_summary", "")
        if not summary:
            order = " > ".join(f"{c.case_id}({c.priority_level})" for c in result_cases)
            summary = f"Thu tu uu tien cuu ho: {order}"

        return PriorityReport(cases=result_cases, overall_summary=summary)
