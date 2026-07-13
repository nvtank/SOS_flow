"""
EmergencyPrioritizer — So sánh và xếp hạng ưu tiên cứu hộ.

Kết hợp 2 tầng:
  1. Rule-based scoring: tính điểm nhanh, deterministic
  2. LLM (Bedrock): so sánh ngữ cảnh, giải thích lý do bằng ngôn ngữ tự nhiên
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from .schemas import AIAnalysis, PrioritizedCase, PriorityReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule-based scoring
# ---------------------------------------------------------------------------
def _score_level(score: float) -> str:
    """Chuyển điểm số thành mức ưu tiên."""
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def rule_based_score(analysis: AIAnalysis) -> float:
    """
    Tính điểm ưu tiên dựa trên rule cứng (0-100).

    Trọng số:
      - Trapped:        +30
      - Injured:        +5 mỗi người (max +25)
      - Children:       +4 mỗi trẻ (max +16)
      - Elderly:        +4 mỗi người già (max +16)
      - Water level:    +3 mỗi 0.5m (max +18)
      - People:         +1 mỗi người (max +10)
      - Risks:          +3 mỗi risk (max +15)
      - Needs:          +2 mỗi need (max +10)
    """
    score = 0.0

    # Trapped — yếu tố quan trọng nhất
    if analysis.is_trapped:
        score += 30

    # Injured
    injured = analysis.number_of_injured or 0
    score += min(injured * 5, 25)

    # Vulnerable people
    children = analysis.number_of_children or 0
    score += min(children * 4, 16)

    elderly = analysis.number_of_elderly or 0
    score += min(elderly * 4, 16)

    # Water level
    if analysis.water_level is not None and analysis.water_level > 0:
        score += min(analysis.water_level / 0.5 * 3, 18)

    # Total people
    people = analysis.number_of_people or 0
    score += min(people * 1, 10)

    # Risks
    score += min(len(analysis.detected_risks) * 3, 15)

    # Needs
    score += min(len(analysis.needs) * 2, 10)

    return min(100.0, round(score, 1))


def rule_based_reasoning(analysis: AIAnalysis, score: float) -> str:
    """Tạo giải thích rule-based đơn giản."""
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

    if not parts:
        parts.append("khong co thong tin chi tiet")

    level = _score_level(score)
    return f"[{level} - {score} diem] " + "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Prioritizer class
# ---------------------------------------------------------------------------
class EmergencyPrioritizer:
    """
    So sánh nhiều case và xếp hạng ưu tiên.

    mode:
      - "rule":    chỉ dùng rule-based scoring
      - "bedrock": rule-based + LLM giải thích (mặc định)
    """

    def __init__(self, mode: str = "bedrock") -> None:
        self.mode = mode.lower()
        self._client = None  # lazy init
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
        Xếp hạng ưu tiên cho nhiều case.

        Args:
            cases: dict mapping case_id -> AIAnalysis

        Returns:
            PriorityReport với cases đã sắp xếp theo ưu tiên giảm dần
        """
        if not cases:
            return PriorityReport(
                cases=[],
                overall_summary="Khong co case nao de so sanh.",
            )

        # Bước 1: Rule-based scoring
        scored: list[PrioritizedCase] = []
        for case_id, analysis in cases.items():
            score = rule_based_score(analysis)
            level = _score_level(score)
            reasoning = rule_based_reasoning(analysis, score)
            scored.append(PrioritizedCase(
                case_id=case_id,
                priority_score=score,
                priority_level=level,
                reasoning=reasoning,
                original_analysis=analysis,
            ))

        # Sắp xếp theo điểm giảm dần
        scored.sort(key=lambda c: c.priority_score, reverse=True)

        # Bước 2: LLM comparison (nếu mode=bedrock và có >= 2 case)
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
    # LLM comparison
    # ------------------------------------------------------------------
    async def _llm_compare(
        self,
        scored_cases: list[PrioritizedCase],
    ) -> PriorityReport | None:
        """Gọi Bedrock để so sánh và giải thích ưu tiên."""
        client = self._get_bedrock_client()
        if client is None:
            return None

        invoke_target = (
            os.getenv("BEDROCK_INFERENCE_PROFILE_ID")
            or os.getenv("BEDROCK_MODEL_ID", "")
        )
        if not invoke_target:
            return None

        max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "2048"))

        # Build user prompt
        cases_json: list[dict[str, Any]] = []
        for case in scored_cases:
            case_data = {
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
            cases_json.append(case_data)

        user_content = (
            f"Compare the following {len(cases_json)} emergency cases "
            f"and rank by rescue priority:\n\n"
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

            # Extract text
            output_msg = response.get("output", {}).get("message", {})
            content_blocks = output_msg.get("content", [])
            text = "\n".join(
                b["text"] for b in content_blocks
                if isinstance(b, dict) and "text" in b
            )
            logger.info("Priority comparison OK - %.2fs, %d chars", elapsed, len(text))

            # Parse JSON
            parsed = self._extract_json(text)
            return self._build_report(parsed, scored_cases)

        except Exception as exc:
            logger.warning("LLM priority comparison failed: %s", exc)
            return None

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from response text."""
        import re

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
        """Merge LLM ranking with original analysis data."""
        # Map case_id -> original analysis
        case_map = {c.case_id: c.original_analysis for c in scored_cases}

        ranked = llm_data.get("ranked_cases", [])
        result_cases: list[PrioritizedCase] = []

        for item in ranked:
            case_id = item.get("case_id", "")
            original = case_map.get(case_id)
            if original is None:
                continue

            score = float(item.get("priority_score", 0))
            level = item.get("priority_level", _score_level(score))
            reasoning = item.get("reasoning", "No reasoning provided.")

            result_cases.append(PrioritizedCase(
                case_id=case_id,
                priority_score=score,
                priority_level=level,
                reasoning=reasoning,
                original_analysis=original,
            ))

        # Nếu LLM bỏ sót case nào, thêm lại từ rule-based
        seen_ids = {c.case_id for c in result_cases}
        for case in scored_cases:
            if case.case_id not in seen_ids:
                result_cases.append(case)

        # Sort lại
        result_cases.sort(key=lambda c: c.priority_score, reverse=True)

        summary = llm_data.get("overall_summary", "")
        if not summary:
            order = " > ".join(f"{c.case_id}({c.priority_level})" for c in result_cases)
            summary = f"Thu tu uu tien cuu ho: {order}"

        return PriorityReport(cases=result_cases, overall_summary=summary)
