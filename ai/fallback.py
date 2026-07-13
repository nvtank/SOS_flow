"""
RegexFallbackAnalyzer — Fallback parser dùng regex khi Bedrock lỗi.

Đảm bảo extract đủ tất cả field trong AIAnalysis schema,
tương đương khả năng của RuleBasedExtractor trong analyzer.py.
"""

import logging
import re
from typing import Optional

from .schemas import AIAnalysis, ExtractedLocation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled regex patterns (pre-compile cho performance)
# ---------------------------------------------------------------------------

# Số người
_PEOPLE_PATTERN = re.compile(
    r"(\d+)\s*(người|nguoi|người lớn|nguoi lon)",
    re.IGNORECASE,
)

# Trẻ em — đặt "trẻ em" trước "trẻ" để match cụm dài trước
_CHILDREN_PATTERN = re.compile(
    r"(\d+)\s*(trẻ em|tre em|em nhỏ|em nho|em bé|em be|trẻ|tre|bé|be)",
    re.IGNORECASE,
)

# Người già
_ELDERLY_PATTERN = re.compile(
    r"(\d+)\s*(người già|nguoi gia|người cao tuổi|nguoi cao tuoi|cụ già|cu gia|cụ|cu)",
    re.IGNORECASE,
)

# Số người bị thương — extract số lượng thật thay vì hardcode =1
_INJURED_COUNT_PATTERN = re.compile(
    r"(\d+)\s*(người bị thương|nguoi bi thuong|người.{0,5}bị thương|bị thương)",
    re.IGNORECASE,
)

# Mực nước: "1.2 mét", "0,5m", "2 met"
_WATER_LEVEL_PATTERN = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(mét|met|m(?:eters?)?)\b",
    re.IGNORECASE,
)

# Location: extract raw text sau keyword địa chỉ
_LOCATION_PATTERN = re.compile(
    r"\b(tọa độ|toa do|đường|duong|xã|xa|phường|phuong|quận|quan|huyện|huyen|thôn|thon|ấp|ap|tỉnh|tinh|số|so)\s+[^,.\n]{1,40}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Keyword groups
# ---------------------------------------------------------------------------

_INJURY_KEYWORDS = [
    "bị thương", "bi thuong",
    "bất tỉnh", "bat tinh",
    "không thở", "khong tho",
    "chấn thương", "chan thuong",
    "gãy", "gay",
    "chảy máu", "chay mau",
]

_TRAPPED_KEYWORDS = [
    "mắc kẹt", "mac ket",
    "không ra được", "khong ra duoc",
    "kẹt trong", "ket trong",
    "bị kẹt", "bi ket",
    "kẹt", "ket",
    "cô lập", "co lap",
    "không thoát", "khong thoat",
]

# High water — dùng từ cụ thể, KHÔNG dùng "nước" đơn lẻ để tránh false-positive
_HIGH_WATER_KEYWORDS = [
    "ngập", "ngap",
    "nước dâng", "nuoc dang",
    "nước lên", "nuoc len",
    "nước cuốn", "nuoc cuon",
    "ngập nước", "ngap nuoc",
    "lũ lụt", "lu lut",
    "sạt lở", "sat lo",
]

_NEEDS_GROUPS = {
    "medical": ["thuốc", "thuoc", "y tế", "y te", "cấp cứu", "cap cuu", "bác sĩ", "bac si"],
    "food": ["lương thực", "luong thuc", "thực phẩm", "thuc pham", "đồ ăn", "do an", "food"],
    "water": ["nước uống", "nuoc uong", "nước sạch", "nuoc sach"],
    "rescue": ["cứu hộ", "cuu ho", "cứu giúp", "cuu giup", "cứu nạn", "cuu nan"],
    "shelter": ["chỗ ở", "cho o", "lều", "leu", "nơi trú", "noi tru"],
    "electricity": ["điện", "dien", "không có điện", "khong co dien", "mất điện", "mat dien"],
}

_LOCATION_TERMS = [
    "tọa độ", "toa do", "đường", "duong",
    "xã", "xa", "phường", "phuong",
    "quận", "quan", "huyện", "huyen",
    "thôn", "thon", "ấp", "ap",
    "tỉnh", "tinh", "số", "so",
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _extract_int(pattern: re.Pattern, text: str) -> Optional[int]:
    """Extract số nguyên đầu tiên match pattern."""
    match = pattern.search(text)
    if match:
        return int(match.group(1))
    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    """Kiểm tra text có chứa bất kỳ keyword nào."""
    return any(kw in text for kw in keywords)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class RegexFallbackAnalyzer:
    """
    Fallback parser dùng regex khi Bedrock không khả dụng.

    Extract đầy đủ tất cả field trong AIAnalysis:
    - people, children, elderly, injured (số lượng thực)
    - is_trapped, water_level
    - location (raw text)
    - needs, risks, missing_information
    - confidence (tính dựa trên lượng thông tin extract được)
    """

    async def analyze(self, message: str) -> AIAnalysis:
        lower = message.lower()

        # --- Extract numbers ---
        people = _extract_int(_PEOPLE_PATTERN, lower)
        children = _extract_int(_CHILDREN_PATTERN, lower)
        elderly = _extract_int(_ELDERLY_PATTERN, lower)
        injured = _extract_int(_INJURED_COUNT_PATTERN, lower)

        # --- Risks ---
        risks: list[str] = []

        # Injury: nếu có keyword nhưng chưa extract được số → mặc định 1
        if _contains_any(lower, _INJURY_KEYWORDS):
            risks.append("injury")
            if injured is None:
                injured = 1

        # Trapped
        trapped: Optional[bool] = None
        if _contains_any(lower, _TRAPPED_KEYWORDS):
            trapped = True
            risks.append("trapped")

        # High water
        if _contains_any(lower, _HIGH_WATER_KEYWORDS):
            risks.append("high_water")

        # --- Water level ---
        water_level: Optional[float] = None
        water_match = _WATER_LEVEL_PATTERN.search(lower)
        if water_match:
            water_level = float(water_match.group(1).replace(",", "."))
            if "high_water" not in risks:
                risks.append("high_water")

        # --- Needs ---
        needs: list[str] = []
        for label, keywords in _NEEDS_GROUPS.items():
            if _contains_any(lower, keywords):
                needs.append(label)

        # --- Location ---
        location = ExtractedLocation(raw_text=None)
        loc_match = _LOCATION_PATTERN.search(message)  # dùng message gốc (giữ dấu)
        if loc_match:
            location.raw_text = loc_match.group(0).strip()

        # --- Missing information ---
        missing: list[str] = []
        if people is None:
            missing.append("number_of_people")
        if not _contains_any(lower, _LOCATION_TERMS):
            missing.append("exact_location")

        # --- Summary ---
        summary = self._build_summary(trapped, injured, risks)

        # --- Confidence ---
        confidence = self._estimate_confidence(
            people, children, elderly, injured,
            trapped, water_level, needs, risks,
        )

        logger.debug(
            "Fallback result: people=%s children=%s elderly=%s injured=%s "
            "trapped=%s water=%.1s risks=%s needs=%s conf=%.2f",
            people, children, elderly, injured,
            trapped, water_level, risks, needs, confidence,
        )

        return AIAnalysis(
            summary=summary,
            normalized_message=message.strip(),
            extracted_location=location,
            number_of_people=people,
            number_of_children=children,
            number_of_elderly=elderly,
            number_of_injured=injured,
            is_trapped=trapped,
            water_level=water_level,
            needs=needs,
            detected_risks=risks,
            missing_information=missing,
            confidence=confidence,
            explanation="Fallback regex parser (Bedrock unavailable).",
        )

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------
    @staticmethod
    def _build_summary(
        trapped: Optional[bool],
        injured: Optional[int],
        risks: list[str],
    ) -> str:
        if trapped and injured:
            return "Nan nhan mac ket va co dau hieu bi thuong."
        if trapped:
            return "Nan nhan dang mac ket."
        if injured:
            return "Nan nhan co dau hieu bi thuong."
        if risks:
            return "Bao cao co dau hieu rui ro can xu ly."
        return "Emergency report"

    # ------------------------------------------------------------------
    # Confidence estimation
    # ------------------------------------------------------------------
    @staticmethod
    def _estimate_confidence(
        people: Optional[int],
        children: Optional[int],
        elderly: Optional[int],
        injured: Optional[int],
        trapped: Optional[bool],
        water_level: Optional[float],
        needs: list[str],
        risks: list[str],
    ) -> float:
        """
        Confidence dựa trên lượng thông tin extract được.
        Nhiều thông tin hơn → confidence cao hơn.
        """
        score = 0.35  # baseline
        if people is not None:
            score += 0.10
        if children is not None:
            score += 0.05
        if elderly is not None:
            score += 0.05
        if injured is not None:
            score += 0.10
        if trapped is not None:
            score += 0.10
        if water_level is not None:
            score += 0.05
        if needs:
            score += min(len(needs) * 0.03, 0.10)
        if risks:
            score += min(len(risks) * 0.03, 0.10)
        return min(0.85, round(score, 2))


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------
async def fallback_parse(message: str) -> AIAnalysis:
    """Shortcut để parse message bằng regex fallback."""
    analyzer = RegexFallbackAnalyzer()
    return await analyzer.analyze(message)
