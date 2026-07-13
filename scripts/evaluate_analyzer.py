#!/usr/bin/env python3
"""Evaluate mock or Bedrock analyzers against the synthetic SOS dataset."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Support both a checkout (`repo/backend/app`) and the compact API image
# (`/app/app`) without requiring callers to set PYTHONPATH.
repo_root = Path(__file__).resolve().parents[1]
backend_path = repo_root / "backend"
sys.path.insert(0, str(backend_path if (backend_path / "app").is_dir() else repo_root))

from app.core.config import get_settings
from app.services.ai_analyzer import EmergencyAnalysis, analyze_with_fallback


def score_sets(expected: set[str], actual: set[str]) -> tuple[int, int, int]:
    return len(expected & actual), len(actual - expected), len(expected - actual)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock", "bedrock"], default="mock")
    parser.add_argument("--dataset", default="ai/datasets/evaluation.jsonl")
    args = parser.parse_args()
    os.environ["AI_PROVIDER"] = args.provider
    get_settings.cache_clear(); settings = get_settings()
    rows = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    valid = fallback = 0; risk_tp = risk_fp = risk_fn = missing_tp = missing_fp = missing_fn = 0; latencies = []
    for row in rows:
        started = time.perf_counter()
        try:
            analysis, metadata = analyze_with_fallback(row["message"], settings)
            EmergencyAnalysis.model_validate(analysis); valid += 1; fallback += int(bool(metadata["fallback_used"])); latencies.append(metadata["latency_ms"])
            tp, fp, fn = score_sets(set(row["risks"]), set(analysis["detected_risks"])); risk_tp += tp; risk_fp += fp; risk_fn += fn
            tp, fp, fn = score_sets(set(row["missing"]), set(analysis["missing_information"])); missing_tp += tp; missing_fp += fp; missing_fn += fn
        except Exception:
            latencies.append(round((time.perf_counter() - started) * 1000, 1))
    precision = lambda tp, fp: round(tp / (tp + fp), 3) if tp + fp else 0.0
    recall = lambda tp, fn: round(tp / (tp + fn), 3) if tp + fn else 0.0
    print(json.dumps({"provider": args.provider, "records": len(rows), "json_validity": round(valid / len(rows), 3), "risk_precision": precision(risk_tp, risk_fp), "risk_recall": recall(risk_tp, risk_fn), "missing_precision": precision(missing_tp, missing_fp), "missing_recall": recall(missing_tp, missing_fn), "average_latency_ms": round(sum(latencies) / len(latencies), 1), "fallback_rate": round(fallback / len(rows), 3), "estimated_invocation_count": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
