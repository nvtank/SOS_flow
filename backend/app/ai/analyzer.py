import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from .fallback import RegexFallbackAnalyzer
from .schemas import (
    AIAnalysis,
    ExtractedLocation,
)


class EmergencyAnalyzer(ABC):

    @abstractmethod
    async def analyze(
        self,
        message: str,
    ) -> AIAnalysis:
        raise NotImplementedError


@dataclass
class RuleBasedResult:
    number_of_people: int | None = None
    number_of_children: int | None = None
    number_of_elderly: int | None = None
    number_of_injured: int | None = None
    is_trapped: bool | None = None
    water_level: float | None = None
    needs: list[str] = field(default_factory=list)
    detected_risks: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    extracted_location: ExtractedLocation = field(default_factory=lambda: ExtractedLocation(raw_text=None))
    summary: str = "Emergency report"
    confidence: float = 0.5


class RuleBasedExtractor:
    NUMBER_PATTERNS = {
        "people": re.compile(r"(\d+)\s*(người|nguoi)", re.IGNORECASE),
        "children": re.compile(r"(\d+)\s*(trẻ em|tre em|trẻ|em bé|bé)", re.IGNORECASE),
        "injured": re.compile(r"(\d+)\s*(người bị thương|bị thương|injured)", re.IGNORECASE),
    }

    KEYWORD_GROUPS = {
        "injury": ["bị thương", "bất tỉnh", "không thở", "chấn thương", "injury"],
        "trapped": ["mắc kẹt", "không ra được", "kẹt trong", "kẹt", "bị kẹt"],
        "high_water": ["ngập", "nước dâng", "nước lên", "nước cuốn", "ngập nước"],
    }

    NEEDS_GROUPS = {
        "medical": ["thuốc", "y tế", "medical"],
        "food": ["lương thực", "thực phẩm", "food"],
        "water": ["nước uống", "nước", "water"],
    }

    LOCATION_TERMS = ["tọa độ", "đường", "xã", "phường", "quận", "huyện", "thôn", "ấp", "số"]
    LOCATION_PATTERN = re.compile(r"(tọa độ|đường|xã|phường|quận|huyện|thôn|ấp|số)[^,\.\n]*", re.IGNORECASE)
    WATER_LEVEL_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(m|mét|met|meters?)", re.IGNORECASE)

    def extract(self, message: str) -> RuleBasedResult:
        lower = message.lower()
        result = RuleBasedResult()

        result.number_of_people = self._extract_int(self.NUMBER_PATTERNS["people"], lower)
        result.number_of_children = self._extract_int(self.NUMBER_PATTERNS["children"], lower)
        result.number_of_injured = self._extract_int(self.NUMBER_PATTERNS["injured"], lower)

        if any(self._contains(term, lower) for term in self.KEYWORD_GROUPS["trapped"]):
            result.is_trapped = True
            result.detected_risks.append("trapped")

        if any(self._contains(term, lower) for term in self.KEYWORD_GROUPS["injury"]):
            result.detected_risks.append("injury")
            if result.number_of_injured is None:
                result.number_of_injured = 1

        if any(self._contains(term, lower) for term in self.KEYWORD_GROUPS["high_water"]):
            result.detected_risks.append("high_water")

        for label, terms in self.NEEDS_GROUPS.items():
            if any(self._contains(term, lower) for term in terms):
                result.needs.append(label)

        water_match = self.WATER_LEVEL_PATTERN.search(lower)
        if water_match:
            result.water_level = float(water_match.group(1).replace(",", "."))

        location_match = self.LOCATION_PATTERN.search(message)
        if location_match:
            result.extracted_location.raw_text = location_match.group(0).strip()

        result.missing_information = []
        if result.number_of_people is None:
            result.missing_information.append("number_of_people")
        if not any(term in lower for term in self.LOCATION_TERMS):
            result.missing_information.append("exact_location")

        result.summary = self._build_summary(result)
        result.confidence = self._estimate_confidence(result)
        return result

    def _extract_int(self, pattern: re.Pattern, text: str) -> int | None:
        match = pattern.search(text)
        if not match:
            return None
        return int(match.group(1))

    def _contains(self, term: str, text: str) -> bool:
        return term in text

    def _build_summary(self, result: RuleBasedResult) -> str:
        if result.is_trapped and result.number_of_injured:
            return "Nạn nhân mắc kẹt và có dấu hiệu bị thương."
        if result.is_trapped:
            return "Nạn nhân đang mắc kẹt."
        if result.number_of_injured:
            return "Nạn nhân có dấu hiệu bị thương."
        if result.detected_risks:
            return "Báo cáo có dấu hiệu rủi ro cần xử lý."
        return "Emergency report"

    def _estimate_confidence(self, result: RuleBasedResult) -> float:
        score = 0.45
        if result.number_of_people is not None:
            score += 0.1
        if result.number_of_children is not None:
            score += 0.05
        if result.number_of_injured is not None:
            score += 0.1
        if result.is_trapped:
            score += 0.1
        if result.water_level is not None:
            score += 0.05
        if result.needs:
            score += 0.1
        return min(0.95, score)


class HybridEmergencyAnalyzer(EmergencyAnalyzer):
    def __init__(self, mode: str = "mock"):
        self.mode = mode.lower()
        self.rule_extractor = RuleBasedExtractor()
        self.llm_analyzer = None
        if self.mode in {"bedrock", "hybrid"}:
            self.llm_analyzer = self._create_llm_analyzer()

    def _create_llm_analyzer(self) -> EmergencyAnalyzer:
        try:
            from .bedrock import BedrockEmergencyAnalyzer

            return BedrockEmergencyAnalyzer()
        except Exception:
            return RegexFallbackAnalyzer()

    async def analyze(self, message: str) -> AIAnalysis:
        rule_result = self.rule_extractor.extract(message)

        if self.mode == "mock":
            return self._rule_to_analysis(rule_result, message)

        llm_result = await self.llm_analyzer.analyze(message)
        if self.mode == "hybrid":
            return self._merge(rule_result, llm_result, message)

        return llm_result

    def _rule_to_analysis(self, rule_result: RuleBasedResult, message: str) -> AIAnalysis:
        return AIAnalysis(
            summary=rule_result.summary,
            normalized_message=message.strip(),
            extracted_location=rule_result.extracted_location,
            number_of_people=rule_result.number_of_people,
            number_of_children=rule_result.number_of_children,
            number_of_elderly=rule_result.number_of_elderly,
            number_of_injured=rule_result.number_of_injured,
            is_trapped=rule_result.is_trapped,
            water_level=rule_result.water_level,
            needs=rule_result.needs,
            detected_risks=rule_result.detected_risks,
            missing_information=rule_result.missing_information,
            confidence=rule_result.confidence,
            explanation="Rule-based mock analyzer.",
        )

    def _merge(
        self,
        rule_result: RuleBasedResult,
        llm_result: AIAnalysis,
        message: str,
    ) -> AIAnalysis:
        merged = llm_result.model_dump()

        for field in [
            "number_of_people",
            "number_of_children",
            "number_of_elderly",
            "number_of_injured",
            "is_trapped",
            "water_level",
        ]:
            rule_value = getattr(rule_result, field)
            if rule_value is not None:
                merged[field] = rule_value

        merged["needs"] = sorted(set(merged.get("needs", []) + rule_result.needs))
        merged["detected_risks"] = sorted(set(merged.get("detected_risks", []) + rule_result.detected_risks))
        merged["missing_information"] = sorted(set(merged.get("missing_information", []) + rule_result.missing_information))

        if rule_result.extracted_location.raw_text:
            merged["extracted_location"] = rule_result.extracted_location.model_dump()

        merged["summary"] = merged.get("summary") or rule_result.summary
        merged["confidence"] = round(min(1.0, max(float(merged.get("confidence", 0.0)), rule_result.confidence)), 2)
        merged["normalized_message"] = message.strip()
        merged["explanation"] = merged.get("explanation") or "Hybrid rule-based + LLM analysis."
        return AIAnalysis(**merged)


MockEmergencyAnalyzer = HybridEmergencyAnalyzer


class AIAnalyzerFactory:
    @staticmethod
    def create(mode: str = "mock") -> EmergencyAnalyzer:
        return HybridEmergencyAnalyzer(mode=mode)


async def run_analyzer(mode: str, message: str) -> AIAnalysis:
    analyzer = AIAnalyzerFactory.create(mode)
    return await analyzer.analyze(message)
