from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from app.core.time import as_utc, utc_now


@dataclass
class PriorityInput:
    message: str
    number_of_people: int = 1
    number_of_children: int = 0
    number_of_elderly: int = 0
    number_of_injured: int = 0
    has_disabled_person: bool = False
    has_pregnant_person: bool = False
    is_trapped: bool = False
    water_level: float | None = None
    created_at: datetime | None = None


class PriorityEngine:
    def __init__(self, rules_path: Path):
        self.rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))

    def calculate(self, data: PriorityInput, now: datetime | None = None) -> dict:
        score = 0
        reasons: list[str] = []
        message = (data.message or "").lower()

        severity_score = self.rules["default_severity_score"]
        severity_reason = "Nội dung thông thường cần theo dõi"
        for category in self.rules["severity_keywords"].values():
            if any(keyword.lower() in message for keyword in category["keywords"]):
                if category["score"] > severity_score:
                    severity_score = category["score"]
                    severity_reason = "Nội dung có dấu hiệu nguy hiểm cao"
        score += severity_score
        reasons.append(severity_reason)

        people_score = min(data.number_of_people * self.rules["people"]["per_person"], self.rules["people"]["max_score"])
        score += people_score
        if data.number_of_people:
            reasons.append(f"Có {data.number_of_people} người gặp nạn")

        child_score = data.number_of_children * self.rules["vulnerable"]["per_child"]
        elderly_score = data.number_of_elderly * self.rules["vulnerable"]["per_elderly"]
        score += child_score + elderly_score
        if data.number_of_children:
            reasons.append(f"Có {data.number_of_children} trẻ em")
        if data.number_of_elderly:
            reasons.append(f"Có {data.number_of_elderly} người cao tuổi")

        if data.has_disabled_person:
            score += self.rules["vulnerable"]["disabled_person"]
            reasons.append("Có người khuyết tật")
        if data.has_pregnant_person:
            score += self.rules["vulnerable"]["pregnant_person"]
            reasons.append("Có phụ nữ mang thai")

        injured_score = data.number_of_injured * self.rules["injury"]["per_injured"]
        score += injured_score
        if data.number_of_injured:
            reasons.append(f"Có {data.number_of_injured} người bị thương")
        if any(keyword in message for keyword in ["bất tỉnh", "không thở", "bat tinh"]):
            score += self.rules["injury"]["unconscious"]
            reasons.append("Có dấu hiệu bất tỉnh hoặc khó thở")

        if data.is_trapped or any(keyword in message for keyword in ["mắc kẹt", "không ra được", "kẹt trong nhà", "mac ket"]):
            score += self.rules["trapped"]["score"]
            reasons.append("Nạn nhân đang mắc kẹt")

        if data.water_level is not None:
            water_score, water_reason = self._water_score(data.water_level)
            score += water_score
            reasons.append(water_reason)

        if data.created_at:
            calculation_time = as_utc(now or utc_now())
            waited_minutes = max(0, int((calculation_time - as_utc(data.created_at)).total_seconds() // 60))
            waiting_score = min(waited_minutes // self.rules["waiting_time"]["minutes_per_point"], self.rules["waiting_time"]["max_score"])
            if waiting_score:
                score += waiting_score
                reasons.append(f"Đã chờ {waited_minutes} phút chưa hoàn tất xử lý")

        return {
            "priority_score": int(score),
            "priority_level": self._level(score),
            "reasons": reasons,
        }

    def _water_score(self, water_level: float) -> tuple[int, str]:
        rules = self.rules["water_level"]
        if water_level < 0.5:
            return rules["under_0_5"], "Mực nước dưới 0,5 mét"
        if water_level < 1.5:
            return rules["from_0_5_to_1_5"], "Mực nước từ 0,5 đến dưới 1,5 mét"
        if water_level < 2.5:
            return rules["from_1_5_to_2_5"], "Mực nước từ 1,5 đến dưới 2,5 mét"
        return rules["above_2_5"], "Mực nước ước tính từ 2,5 mét trở lên"

    def _level(self, score: int) -> str:
        levels = self.rules["priority_levels"]
        if score <= levels["low_max"]:
            return "LOW"
        if score <= levels["medium_max"]:
            return "MEDIUM"
        if score <= levels["high_max"]:
            return "HIGH"
        return "CRITICAL"
