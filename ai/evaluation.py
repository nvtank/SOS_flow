import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.analyzer import AIAnalyzerFactory
from app.ai.schemas import AIAnalysis


class EvaluationResult:
    def __init__(self) -> None:
        self.total = 0
        self.correct_people = 0
        self.correct_injured = 0
        self.correct_trapped = 0
        self.correct_json = 0
        self.total_latency = 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "samples": self.total,
            "accuracy_people": self._pct(self.correct_people),
            "accuracy_injured": self._pct(self.correct_injured),
            "accuracy_trapped": self._pct(self.correct_trapped),
            "json_valid": self._pct(self.correct_json),
            "average_latency": self._avg_latency(),
        }

    def _pct(self, value: int) -> str:
        if self.total == 0:
            return "0%"
        return f"{round(value / self.total * 100)}%"

    def _avg_latency(self) -> str:
        if self.total == 0:
            return "0s"
        return f"{round(self.total_latency / self.total, 2)}s"


def load_dataset(path: Path) -> list[dict[str, Any]]:
    json_text = path.read_text(encoding="utf-8")
    dataset = json.loads(json_text)
    if not isinstance(dataset, list):
        raise ValueError("Evaluation dataset must be a JSON list.")
    return dataset


def compare_analysis(pred: AIAnalysis, expected: dict[str, Any]) -> tuple[bool, bool, bool]:
    return (
        pred.number_of_people == expected.get("people"),
        pred.number_of_injured == expected.get("injured"),
        pred.is_trapped == expected.get("trapped"),
    )


async def evaluate(mode: str = "mock", verbose: bool = False) -> EvaluationResult:
    dataset_path = Path(__file__).parent / "datasets" / "eval.json"
    dataset = load_dataset(dataset_path)
    result = EvaluationResult()

    for index, sample in enumerate(dataset, start=1):
        message = sample["input"]
        expected = sample.get("expected", {})
        analyzer = AIAnalyzerFactory.create(mode)
        start = __import__("time").time()
        analysis = await analyzer.analyze(message)
        elapsed = __import__("time").time() - start
        result.total += 1
        result.total_latency += elapsed
        if isinstance(analysis, AIAnalysis):
            result.correct_json += 1
        people_ok, injured_ok, trapped_ok = compare_analysis(analysis, expected)
        result.correct_people += int(people_ok)
        result.correct_injured += int(injured_ok)
        result.correct_trapped += int(trapped_ok)

        if verbose:
            print(f"--- Sample {index} ---")
            print(f"Input: {message}")
            print(f"Expected: {json.dumps(expected, ensure_ascii=False)}")
            print("Predicted:")
            print(analysis.model_dump_json(indent=2, ensure_ascii=False))
            print(f"Elapsed: {elapsed:.3f}s")
            print(f"People OK: {people_ok}, Injured OK: {injured_ok}, Trapped OK: {trapped_ok}")
            print()

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AI analysis on the emergency dataset.")
    parser.add_argument("mode", nargs="?", default="mock", choices=["mock", "hybrid", "bedrock"], help="Analyzer mode to use.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed sample outputs.")
    args = parser.parse_args()

    import asyncio

    report = asyncio.run(evaluate(args.mode, verbose=args.verbose))
    print("Evaluation results")
    for key, value in report.summary().items():
        print(f"{key}: {value}")
