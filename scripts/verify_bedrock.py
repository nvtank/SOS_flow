#!/usr/bin/env python3
"""Make one real Bedrock analysis call and print non-secret proof metadata."""

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
backend_path = repo_root / "backend"
sys.path.insert(0, str(backend_path if (backend_path / "app").is_dir() else repo_root))

from app.core.config import get_settings
from app.services.ai_analyzer import EmergencyAnalysis, analyze_with_fallback


DEMO_REPORT = "Khẩn cấp tại Thôn 3, Xã Trà Linh, Đà Nẵng: 6 người, có 2 trẻ em và 1 người bị thương đang mắc kẹt, nước cao khoảng 2,8 mét."


def main() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    if settings.ai_provider.lower() != "bedrock":
        raise SystemExit("AI_PROVIDER must be bedrock; refusing to treat mock/fallback output as proof.")

    analysis, metadata = analyze_with_fallback(DEMO_REPORT, settings)
    EmergencyAnalysis.model_validate(analysis)
    if metadata["provider"] != "bedrock" or metadata["fallback_used"]:
        raise SystemExit(f"Bedrock proof failed safely: provider={metadata['provider']}, fallback={metadata['fallback_used']}, error={metadata['error_code']}")

    # Keep output presentation-safe: no credentials, raw provider response, or PII.
    print(json.dumps({
        "bedrock_verified": True,
        "provider": metadata["provider"],
        "model_id_suffix": (metadata.get("model_id") or "")[-40:],
        "latency_ms": metadata["latency_ms"],
        "fallback_used": metadata["fallback_used"],
        "error_code": metadata["error_code"],
        "confidence": analysis["confidence"],
        "detected_risks": analysis["detected_risks"],
        "missing_information": analysis["missing_information"],
        "summary": analysis["summary"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
