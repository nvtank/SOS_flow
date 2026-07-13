import re
from abc import ABC, abstractmethod


class EmergencyAnalyzer(ABC):
    @abstractmethod
    def analyze(self, message: str) -> dict:
        raise NotImplementedError


class MockEmergencyAnalyzer(EmergencyAnalyzer):
    def analyze(self, message: str) -> dict:
        normalized = message.lower()
        risks: list[str] = []
        if any(word in normalized for word in ["mắc kẹt", "không ra được", "kẹt", "mac ket"]):
            risks.append("trapped")
        if any(word in normalized for word in ["ngập nóc", "nước lên", "nước cuốn", "đang chìm"]):
            risks.append("high_water")
        if any(word in normalized for word in ["trẻ em", "tre em", "em bé"]):
            risks.append("children")
        if any(word in normalized for word in ["bị thương", "bất tỉnh", "không thở"]):
            risks.append("injury")

        missing_information: list[str] = []
        if not re.search(r"\d+|đường|xã|phường|cầu|thôn|ấp|quận|huyện", normalized):
            missing_information.append("exact_location")
        if not re.search(r"\d+\s*(người|nguoi)", normalized):
            missing_information.append("number_of_people")

        summary = "Yêu cầu cứu hộ cần xác minh thêm thông tin."
        if "trapped" in risks and "high_water" in risks:
            summary = "Nạn nhân có dấu hiệu mắc kẹt trong khu vực nước dâng cao."
        elif "injury" in risks:
            summary = "Yêu cầu có dấu hiệu người bị thương hoặc nguy hiểm sức khỏe."
        elif risks:
            summary = "Yêu cầu có dấu hiệu rủi ro cần điều phối theo dõi."

        confidence = min(0.9, 0.55 + len(risks) * 0.1)
        return {
            "summary": summary,
            "detected_risks": risks,
            "missing_information": missing_information,
            "confidence": round(confidence, 2),
        }
