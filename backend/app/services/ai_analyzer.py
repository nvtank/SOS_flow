"""Explainable analyzers with an optional Amazon Bedrock Converse provider."""

import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings, get_settings
from app.core.time import utc_now


class ExtractedLocation(BaseModel):
    raw_text: str | None = None
    province: str | None = None
    district: str | None = None
    commune: str | None = None
    village: str | None = None


class EmergencyAnalysis(BaseModel):
    summary: str
    normalized_message: str
    extracted_location: ExtractedLocation = Field(default_factory=ExtractedLocation)
    number_of_people: int | None = Field(default=None, ge=0)
    number_of_children: int | None = Field(default=None, ge=0)
    number_of_elderly: int | None = Field(default=None, ge=0)
    number_of_injured: int | None = Field(default=None, ge=0)
    is_trapped: bool | None = None
    water_level: float | None = Field(default=None, ge=0)
    needs: list[str] = Field(default_factory=list)
    detected_risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    explanation: str


EMERGENCY_ANALYSIS_SCHEMA = EmergencyAnalysis.model_json_schema()


def _preserve_explicit_facts(payload: dict[str, Any], message: str) -> None:
    """Prevent a model from changing plainly stated location/risk facts."""
    normalized = message.casefold()
    location = dict(payload.get("extracted_location") or {})
    unknown_values = {"", "không rõ", "khong ro", "unknown", "n/a", "none", "null"}
    for field in ("raw_text", "province", "district", "commune", "village"):
        value = location.get(field)
        if isinstance(value, str) and value.strip().casefold() in unknown_values:
            location[field] = None
    location_evidence = re.search(
        r"\b(?:ở|tại|đường|phố|xã|phường|quận|huyện|thôn|ấp|cầu|kiệt|hẻm|tổ|số\s+nhà)\b",
        normalized,
    )
    if not location_evidence:
        # A model occasionally copies the whole SOS sentence into raw_text.
        # Without any location cue, every location field must remain unknown.
        location = {field: None for field in ("raw_text", "province", "district", "commune", "village")}
    payload["extracted_location"] = location

    location_match = re.search(r"\b(đường\s+[^,.;]+(?:\s*,\s*[^,.;]+)?)", message, flags=re.IGNORECASE)
    if location_match:
        explicit_location = re.split(
            r"\s+(?:cùng|với|đang|hiện|gồm|có\s+\d+|nước\s+đang)\b",
            location_match.group(1),
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" ,")
        location["raw_text"] = explicit_location
        if re.search(r"ngũ\s+hành\s+sơn", normalized):
            location["district"] = "Ngũ Hành Sơn"
        payload["extracted_location"] = location

    water_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(mét|met|m|cm)\b", normalized)
    if water_match:
        explicit_water = float(water_match.group(1).replace(",", "."))
        if water_match.group(2) == "cm":
            explicit_water /= 100
        payload["water_level"] = explicit_water
    else:
        payload["water_level"] = None

    if not re.search(r"trẻ\s+em|trẻ\s+nhỏ|em\s+bé|con\s+nhỏ|tre\s+em", normalized):
        payload["number_of_children"] = None
    if not re.search(r"bị\s+thương|chấn\s+thương|chảy\s+máu|bất\s+tỉnh|không\s+thở|bi\s+thuong", normalized):
        payload["number_of_injured"] = None

    if payload.get("number_of_people") == 0:
        payload["number_of_people"] = None

    trapped_evidence = re.search(r"mắc\s+kẹt|không\s+ra\s+được|kẹt\s+trong|mac\s+ket", normalized)
    risks = list(dict.fromkeys(payload.get("detected_risks", [])))
    if trapped_evidence:
        payload["is_trapped"] = True
        if "trapped" not in risks:
            risks.append("trapped")
    else:
        payload["is_trapped"] = None
        risks = [item for item in risks if item != "trapped"]

    life_threatening = re.search(
        r"sắp\s+chết|sap\s+chet|không\s+thở|khong\s+tho|bất\s+tỉnh|bat\s+tinh|"
        r"không\s+sống\s+qua|khong\s+song\s+qua|không\s+trụ\s+nổi|khong\s+tru\s+noi|"
        r"không\s+cầm\s+cự|khong\s+cam\s+cu|đang\s+chìm|dang\s+chim|nước\s+cuốn|nuoc\s+cuon",
        normalized,
    )
    if life_threatening:
        if "life_threatening" not in risks:
            risks.append("life_threatening")
        payload["summary"] = "Tin báo có dấu hiệu đe dọa tính mạng; cần xác minh và điều phối ngay."
    payload["detected_risks"] = risks

    explicit_single_elderly = re.search(r"(?:mẹ|má|cha|bố|ba|ông|bà)\s+(?:già|cao\s+tuổi)", normalized)
    explicit_elderly = explicit_single_elderly or re.search(r"người\s+già|cao\s+tuổi|cụ\s+già|lão", normalized)
    if not explicit_elderly:
        payload["number_of_elderly"] = None
        payload["detected_risks"] = [item for item in payload.get("detected_risks", []) if item != "elderly"]
    elif explicit_single_elderly:
        payload["number_of_elderly"] = 1
        if "elderly" not in payload.get("detected_risks", []):
            payload.setdefault("detected_risks", []).append("elderly")
        together_with_reporter = re.search(
            r"\b(?:tôi|mình)\b.*\b(?:cùng|với|có|đang\s+có)\s+(?:mẹ|má|cha|bố|ba|ông|bà)\s+(?:già|cao\s+tuổi)",
            normalized,
        )
        if together_with_reporter:
            payload["number_of_people"] = max(2, int(payload.get("number_of_people") or 0))

    missing = list(dict.fromkeys(payload.get("missing_information", [])))
    if location.get("raw_text"):
        missing = [item for item in missing if item != "exact_location"]
    elif "exact_location" not in missing:
        missing.append("exact_location")
    if payload.get("number_of_people") is not None:
        missing = [item for item in missing if item != "number_of_people"]
    elif "number_of_people" not in missing:
        missing.append("number_of_people")
    if payload.get("water_level") is None and "high_water" in payload.get("detected_risks", []) and "water_level" not in missing:
        missing.append("water_level")
    payload["missing_information"] = missing

    if not payload.get("needs"):
        risks = set(payload.get("detected_risks", []))
        payload["needs"] = ["medical_support"] if "injury" in risks else ["rescue"] if risks.intersection({"trapped", "high_water"}) else ["assessment"]


class EmergencyAnalyzer(ABC):
    provider_name = "unknown"

    @abstractmethod
    def analyze(self, message: str) -> EmergencyAnalysis:
        raise NotImplementedError


class MockEmergencyAnalyzer(EmergencyAnalyzer):
    provider_name = "mock"

    def analyze(self, message: str) -> EmergencyAnalysis:
        normalized = message.lower()
        risks: list[str] = []
        if any(word in normalized for word in ["mắc kẹt", "không ra được", "kẹt", "mac ket"]): risks.append("trapped")
        if any(word in normalized for word in ["ngập nóc", "nước lên", "nước cuốn", "đang chìm"]): risks.append("high_water")
        if any(word in normalized for word in ["trẻ em", "tre em", "em bé"]): risks.append("children")
        if any(word in normalized for word in ["bị thương", "bất tỉnh", "không thở"]): risks.append("injury")
        missing = []
        if not re.search(r"\d+|đường|xã|phường|cầu|thôn|ấp|quận|huyện", normalized): missing.append("exact_location")
        if not re.search(r"\d+\s*(người|nguoi)", normalized): missing.append("number_of_people")
        people = re.search(r"(\d+)\s*(người|nguoi)", normalized)
        summary = "Yêu cầu cứu hộ cần xác minh thêm thông tin."
        if "trapped" in risks and "high_water" in risks: summary = "Nạn nhân có dấu hiệu mắc kẹt trong khu vực nước dâng cao."
        elif "injury" in risks: summary = "Yêu cầu có dấu hiệu người bị thương hoặc nguy hiểm sức khỏe."
        elif risks: summary = "Yêu cầu có dấu hiệu rủi ro cần điều phối theo dõi."
        return EmergencyAnalysis(
            summary=summary, normalized_message=normalized, extracted_location=ExtractedLocation(raw_text=None), number_of_people=int(people.group(1)) if people else None,
            is_trapped=True if "trapped" in risks else None, needs=["medical_support"] if "injury" in risks else ["rescue" if "trapped" in risks else "assessment"],
            detected_risks=risks, missing_information=missing, confidence=min(0.9, 0.55 + len(risks) * 0.1), explanation="Rule-based mock analyzer for local/demo fallback.",
        )


class BedrockEmergencyAnalyzer(EmergencyAnalyzer):
    provider_name = "bedrock"

    def __init__(self, settings: Settings, client: Any | None = None):
        self.settings = settings
        self.model_id = settings.bedrock_custom_model_arn or settings.bedrock_inference_profile_arn or settings.bedrock_model_id
        if not self.model_id:
            raise ValueError("BEDROCK_MODEL_ID, BEDROCK_INFERENCE_PROFILE_ARN, or BEDROCK_CUSTOM_MODEL_ARN is required")
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client("bedrock-runtime", region_name=settings.aws_region, config=Config(read_timeout=settings.bedrock_timeout_seconds, retries={"max_attempts": settings.bedrock_max_retries, "mode": "standard"}))
        self.client = client

    def analyze(self, message: str) -> EmergencyAnalysis:
        prompt = """Bạn là bộ trích xuất tin SOS tiếng Việt cho điều phối viên cứu hộ.
Chỉ gọi tool submit_emergency_analysis. Không thêm diễn giải bên ngoài tool và không bịa dữ kiện.

Yêu cầu bắt buộc:
- summary và explanation viết bằng tiếng Việt, ngắn gọn, dễ đọc.
- Trích xuất mọi số lượng/địa điểm được nêu rõ trong tin.
- number_of_people là tổng tất cả nạn nhân, bao gồm trẻ em; number_of_children là tập con.
- Chỉ gắn elderly, disabled_person hoặc pregnant_person khi tin nói rõ. Không suy diễn từ cụm "người nhà".
- Giữ nguyên chính tả địa danh trong tin báo; nếu có đường/xã/phường/quận thì raw_text phải là đúng cụm địa danh đó. Không đánh dấu exact_location là thiếu khi đã có cụm địa danh cụ thể.
- detected_risks chỉ dùng các nhãn: life_threatening, trapped, high_water, injury, children, elderly, landslide, disabled_person, pregnant_person. Thêm life_threatening khi có các cụm như "sắp chết", "không thở", "bất tỉnh", "không trụ nổi" hoặc nguy cơ tử vong trực tiếp.
- missing_information liệt kê các thông tin quan trọng còn thiếu, ví dụ exact_location, number_of_people, contact_method.
- confidence từ 0 đến 1. Nếu không chắc, dùng null cho trường dữ liệu thay vì suy đoán.

Tin SOS cần phân tích:
""" + message
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            toolConfig={"tools": [{"toolSpec": {"name": "submit_emergency_analysis", "description": "Return validated emergency analysis", "inputSchema": {"json": EMERGENCY_ANALYSIS_SCHEMA}}}], "toolChoice": {"tool": {"name": "submit_emergency_analysis"}}},
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        tool_use = next((item.get("toolUse") for item in content if item.get("toolUse", {}).get("name") == "submit_emergency_analysis"), None)
        if not tool_use:
            raise ValueError("Bedrock response did not contain structured tool output")
        # Nova can occasionally omit bookkeeping fields even when it returns a
        # valid tool call. Complete only deterministic fields from the original
        # report instead of discarding a useful Bedrock extraction and falling
        # all the way back to the mock analyzer.
        payload = dict(tool_use.get("input") or {})
        payload.setdefault("normalized_message", " ".join(message.casefold().split()))
        payload.setdefault("summary", "AI đã phân tích tin SOS; điều phối viên cần xác minh.")
        payload.setdefault("explanation", "Structured analysis generated by Amazon Bedrock.")
        payload.setdefault("confidence", 0.6)
        payload.setdefault("extracted_location", {})
        payload.setdefault("needs", ["assessment"])
        payload.setdefault("detected_risks", [])
        payload.setdefault("missing_information", [])
        _preserve_explicit_facts(payload, message)
        if payload.get("is_trapped") is None and "trapped" in payload["detected_risks"]:
            payload["is_trapped"] = True
        return EmergencyAnalysis.model_validate(payload)


def _safe_error_code(error: Exception) -> str:
    # Class and message matching intentionally only yields a coarse operational
    # category.  It is safe to persist and never includes a provider response.
    description = f"{error.__class__.__name__} {error}".lower()
    if "timeout" in description: return "TIMEOUT"
    if "thrott" in description: return "THROTTLED"
    # AccessDenied messages contain "not authorized"; classify model/IAM
    # access before credential matching so they are not mislabeled as broken
    # credentials.
    if "access" in description or "model" in description or "inference profile" in description: return "MODEL_ACCESS_ERROR"
    if "credential" in description or "unrecognizedclient" in description or "invalid security token" in description: return "CREDENTIAL_ERROR"
    if "validation" in description or "json" in description or "structured" in description or "tool output" in description or "invalid" in description: return "INVALID_STRUCTURED_OUTPUT"
    return "ANALYZER_ERROR"


def get_emergency_analyzer(settings: Settings | None = None) -> EmergencyAnalyzer:
    settings = settings or get_settings()
    if settings.ai_provider.lower() == "mock": return MockEmergencyAnalyzer()
    if settings.ai_provider.lower() == "bedrock": return BedrockEmergencyAnalyzer(settings)
    raise ValueError("AI_PROVIDER must be mock or bedrock")


def analyze_with_fallback(message: str, settings: Settings | None = None) -> tuple[dict, dict]:
    settings = settings or get_settings(); started = time.perf_counter(); fallback = False; error_code = None
    requested_provider = settings.ai_provider.lower()
    try:
        analyzer = get_emergency_analyzer(settings); analysis = analyzer.analyze(message)
    except (Exception, ValidationError) as error:
        if not settings.ai_fallback_enabled: raise
        analyzer = MockEmergencyAnalyzer(); analysis = analyzer.analyze(message); fallback = True; error_code = _safe_error_code(error)
    metadata = {
        "provider": analyzer.provider_name,
        "requested_provider": requested_provider,
        "model_id": (getattr(analyzer, "model_id", None) or "mock")[-80:],
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "analyzed_at": utc_now().isoformat(),
        "confidence": analysis.confidence,
        "ai_invoked": requested_provider == "bedrock",
        "bedrock_succeeded": analyzer.provider_name == "bedrock" and not fallback,
        "fallback_used": fallback,
        "error_code": error_code,
    }
    return analysis.model_dump(mode="json"), metadata
