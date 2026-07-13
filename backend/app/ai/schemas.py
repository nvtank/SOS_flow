from typing import List, Optional

from pydantic import BaseModel, Field


class ExtractedLocation(BaseModel):
    raw_text: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    commune: Optional[str] = None
    village: Optional[str] = None


class AIAnalysis(BaseModel):
    summary: str

    normalized_message: str

    extracted_location: ExtractedLocation

    number_of_people: Optional[int] = None

    number_of_children: Optional[int] = None

    number_of_elderly: Optional[int] = None

    number_of_injured: Optional[int] = None

    is_trapped: Optional[bool] = None

    water_level: Optional[float] = None

    needs: List[str] = Field(default_factory=list)

    detected_risks: List[str] = Field(default_factory=list)

    missing_information: List[str] = Field(default_factory=list)

    confidence: float = Field(ge=0.0, le=1.0)

    explanation: str


# ---------------------------------------------------------------------------
# Priority ranking schemas
# ---------------------------------------------------------------------------
class PrioritizedCase(BaseModel):
    """Một case đã được xếp hạng ưu tiên."""

    case_id: str = Field(description="ID hoặc label của case")
    priority_score: float = Field(
        ge=0.0, le=100.0,
        description="Điểm ưu tiên 0-100 (100 = khẩn cấp nhất)",
    )
    priority_level: str = Field(
        description="Mức ưu tiên: CRITICAL / HIGH / MEDIUM / LOW",
    )
    reasoning: str = Field(
        description="Giải thích lý do xếp hạng ưu tiên",
    )
    original_analysis: AIAnalysis


class PriorityReport(BaseModel):
    """Kết quả so sánh và xếp hạng nhiều case."""

    cases: List[PrioritizedCase] = Field(
        description="Danh sách case đã sắp xếp theo ưu tiên giảm dần",
    )
    overall_summary: str = Field(
        description="Tóm tắt tổng thể tình hình và khuyến nghị",
    )