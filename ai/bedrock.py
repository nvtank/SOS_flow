"""
BedrockEmergencyAnalyzer — Gọi AWS Bedrock qua Converse API.

Converse API là API chuẩn nhất của Bedrock, tự động xử lý format
request/response cho mọi model (Claude, Nova, Titan...).
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env cục bộ (nếu có) — ưu tiên thấp hơn biến môi trường thật
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH, override=False)

# ---------------------------------------------------------------------------
# boto3 import — graceful nếu chưa cài
# ---------------------------------------------------------------------------
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    boto3 = None
    BotoCoreError = ClientError = Exception

from .fallback import RegexFallbackAnalyzer
from .schemas import AIAnalysis, ExtractedLocation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------
_RETRYABLE_ERROR_CODES = frozenset({
    "ThrottlingException",
    "ModelTimeoutException",
    "ServiceUnavailableException",
    "InternalServerException",
})

_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # giây


def _is_retryable(exc: Exception) -> bool:
    """Kiểm tra xem lỗi có nên retry không."""
    error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    return error_code in _RETRYABLE_ERROR_CODES


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class BedrockEmergencyAnalyzer:
    """Phân tích báo cáo khẩn cấp bằng AWS Bedrock Converse API."""

    def __init__(self) -> None:
        if boto3 is None:
            raise RuntimeError(
                "boto3 is required. Install: pip install boto3"
            )

        # Model ID — hỗ trợ cả model ID thường và inference profile ARN
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "")
        self.inference_profile_id = os.getenv("BEDROCK_INFERENCE_PROFILE_ARN") or os.getenv("BEDROCK_INFERENCE_PROFILE_ID", "")
        self.invoke_target = self.inference_profile_id or self.model_id
        if not self.invoke_target:
            raise RuntimeError(
                "Cần set BEDROCK_MODEL_ID hoặc BEDROCK_INFERENCE_PROFILE_ARN trong .env"
            )

        self.max_tokens = int(os.getenv("BEDROCK_MAX_TOKENS", "2048"))
        self.region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

        # Tạo Bedrock Runtime client
        kwargs: dict[str, Any] = {}
        if self.region:
            kwargs["region_name"] = self.region
        self.client = boto3.client("bedrock-runtime", **kwargs)

        # Fallback khi Bedrock lỗi
        self.fallback = RegexFallbackAnalyzer()

        # System prompt
        self._system_prompt_path = (
            Path(__file__).parent / "prompts" / "emergency_system.txt"
        )

        logger.info(
            "BedrockEmergencyAnalyzer initialized — model=%s region=%s",
            self.invoke_target,
            self.region,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def analyze(self, message: str) -> AIAnalysis:
        """Phân tích tin nhắn khẩn cấp, trả về AIAnalysis."""
        try:
            response_text = self._call_converse(message)
            parsed = self._extract_json(response_text)
            result = self._normalize(parsed, message)
            return AIAnalysis(**result)
        except Exception as exc:
            logger.error("Bedrock failed, falling back to regex: %s", exc)
            return await self._handle_fallback(message, str(exc))

    # ------------------------------------------------------------------
    # Gọi Bedrock Converse API (với retry)
    # ------------------------------------------------------------------
    def _call_converse(self, message: str) -> str:
        """Gọi Bedrock Converse API với retry."""
        system_prompt = self._system_prompt_path.read_text(encoding="utf-8")
        user_content = (
            f"User report:\n{message}\n\n"
            "Return only valid JSON matching the schema."
        )

        request_params: dict[str, Any] = {
            "modelId": self.invoke_target,
            "system": [{"text": system_prompt}],
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": user_content}],
                }
            ],
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": 0.1,
            },
        }

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Converse attempt %d/%d — model=%s",
                    attempt, _MAX_RETRIES, self.invoke_target,
                )
                t0 = time.monotonic()
                response = self.client.converse(**request_params)
                elapsed = time.monotonic() - t0

                # Trích xuất text từ response
                output_message = response.get("output", {}).get("message", {})
                content_blocks = output_message.get("content", [])
                text_parts = [
                    block["text"]
                    for block in content_blocks
                    if isinstance(block, dict) and "text" in block
                ]
                result_text = "\n".join(text_parts)

                logger.info(
                    "Converse OK — %.2fs, %d chars, stop=%s",
                    elapsed,
                    len(result_text),
                    response.get("stopReason", "?"),
                )
                logger.debug("Raw response text:\n%s", result_text)
                return result_text

            except (BotoCoreError, ClientError) as exc:
                last_exc = exc
                if _is_retryable(exc) and attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Retryable error (attempt %d/%d): %s — retry in %.1fs",
                        attempt, _MAX_RETRIES, exc, delay,
                    )
                    time.sleep(delay)
                else:
                    raise

        # Không bao giờ tới đây, nhưng type checker cần
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------
    def _extract_json(self, text: str) -> dict[str, Any]:
        """Trích xuất JSON object từ response text."""
        text = text.strip()
        if not text:
            raise ValueError("Empty response from Bedrock")

        # Thử parse trực tiếp
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Xử lý markdown-wrapped JSON: ```json ... ```
        md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if md_match:
            try:
                return json.loads(md_match.group(1))
            except json.JSONDecodeError:
                pass

        # Tìm JSON object đầu tiên trong text
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Cannot extract JSON from Bedrock response: {text[:200]}")

    # ------------------------------------------------------------------
    # Normalize response → dict cho AIAnalysis
    # ------------------------------------------------------------------
    def _normalize(self, data: dict[str, Any], message: str) -> dict[str, Any]:
        """Chuẩn hóa response dict thành format AIAnalysis."""
        # Một số model wrap kết quả trong nested key
        data = self._unwrap(data)

        # Location
        location = data.get("extracted_location") or data.get("location") or {}
        if isinstance(location, str):
            location = {"raw_text": location}

        # Lists
        needs = data.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]

        detected_risks = data.get("detected_risks") or data.get("risks") or []
        if isinstance(detected_risks, str):
            detected_risks = [detected_risks]

        missing_info = data.get("missing_information") or []
        if isinstance(missing_info, str):
            missing_info = [missing_info]

        return {
            "summary": data.get("summary") or "Emergency report",
            "normalized_message": data.get("normalized_message") or message.strip(),
            "extracted_location": ExtractedLocation(**location),
            "number_of_people": self._get_first(
                data, ["number_of_people", "people", "person_count", "num_people"]
            ),
            "number_of_children": self._get_first(
                data, ["number_of_children", "children"]
            ),
            "number_of_elderly": self._get_first(
                data, ["number_of_elderly", "elderly"]
            ),
            "number_of_injured": self._get_first(
                data, ["number_of_injured", "injured"]
            ),
            "is_trapped": self._get_first(
                data, ["is_trapped", "trapped", "need_rescue", "rescue_needed"]
            ),
            "water_level": self._parse_water_level(
                self._get_first(data, ["water_level", "waterlevel", "water"])
            ),
            "needs": needs,
            "detected_risks": detected_risks,
            "missing_information": missing_info,
            "confidence": float(data.get("confidence") or 0.0),
            "explanation": data.get("explanation") or "Analyzed by Bedrock Converse API.",
        }

    def _unwrap(self, data: dict[str, Any]) -> dict[str, Any]:
        """Unwrap nested response nếu model wrap trong 1 key."""
        if not isinstance(data, dict):
            return {}
        for key in ("incident_report", "report", "result", "data", "response", "output"):
            if key in data and isinstance(data[key], dict):
                return data[key]
        # Nếu chỉ có 1 nested dict, unwrap nó
        nested = [v for v in data.values() if isinstance(v, dict)]
        if len(nested) == 1 and len(data) <= 3:
            return nested[0]
        return data

    def _get_first(self, data: dict[str, Any], keys: list[str]) -> Any:
        """Lấy giá trị đầu tiên tìm thấy theo danh sách keys."""
        for key in keys:
            if key in data:
                return data[key]
        return None

    def _parse_water_level(self, value: Any) -> float | None:
        """Parse water level từ nhiều dạng input."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = (
                value.strip()
                .lower()
                .replace("meters", "")
                .replace("mét", "")
                .replace("met", "")
                .replace("m", "")
                .strip()
            )
            try:
                return float(cleaned.replace(",", "."))
            except ValueError:
                return None
        return None

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    async def _handle_fallback(self, message: str, error: str) -> AIAnalysis:
        """Dùng regex fallback khi Bedrock lỗi."""
        fallback = await self.fallback.analyze(message)
        fallback.explanation = (
            f"Bedrock failed ({error}), used regex fallback."
        )
        return fallback
