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
- detected_risks chỉ dùng các nhãn: trapped, high_water, injury, children, elderly, landslide, disabled_person, pregnant_person. Thêm tất cả nhãn có bằng chứng rõ ràng.
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
        return EmergencyAnalysis.model_validate(tool_use.get("input"))


def _safe_error_code(error: Exception) -> str:
    # Class and message matching intentionally only yields a coarse operational
    # category.  It is safe to persist and never includes a provider response.
    description = f"{error.__class__.__name__} {error}".lower()
    if "timeout" in description: return "TIMEOUT"
    if "thrott" in description: return "THROTTLED"
    if "credential" in description or "auth" in description: return "CREDENTIAL_ERROR"
    if "access" in description or "model" in description or "inference profile" in description: return "MODEL_ACCESS_ERROR"
    if "validation" in description or "json" in description or "structured" in description or "tool output" in description or "invalid" in description: return "INVALID_STRUCTURED_OUTPUT"
    return "ANALYZER_ERROR"


def get_emergency_analyzer(settings: Settings | None = None) -> EmergencyAnalyzer:
    settings = settings or get_settings()
    if settings.ai_provider.lower() == "mock": return MockEmergencyAnalyzer()
    if settings.ai_provider.lower() == "bedrock": return BedrockEmergencyAnalyzer(settings)
    raise ValueError("AI_PROVIDER must be mock or bedrock")


def analyze_with_fallback(message: str, settings: Settings | None = None) -> tuple[dict, dict]:
    settings = settings or get_settings(); started = time.perf_counter(); fallback = False; error_code = None
    try:
        analyzer = get_emergency_analyzer(settings); analysis = analyzer.analyze(message)
    except (Exception, ValidationError) as error:
        if not settings.ai_fallback_enabled: raise
        analyzer = MockEmergencyAnalyzer(); analysis = analyzer.analyze(message); fallback = True; error_code = _safe_error_code(error)
    metadata = {"provider": analyzer.provider_name, "model_id": (getattr(analyzer, "model_id", None) or "mock")[-80:], "latency_ms": round((time.perf_counter() - started) * 1000, 1), "analyzed_at": utc_now().isoformat(), "confidence": analysis.confidence, "fallback_used": fallback, "error_code": error_code}
    return analysis.model_dump(mode="json"), metadata
