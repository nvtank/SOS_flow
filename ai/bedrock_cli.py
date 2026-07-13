"""
Interactive CLI de test he thong AI voi Bedrock that.

Cach dung (tu repository root):
    python -m ai.bedrock_cli                # mac dinh mode=bedrock
    python -m ai.bedrock_cli --mode hybrid   # dung hybrid (rule + LLM)
    python -m ai.bedrock_cli --mode mock      # dung mock (chi rule-based)

Trong terminal:
    - Nhap cau bao cao khan cap -> nhan ket qua phan tich JSON
    - Go 'compare' de vao che do so sanh uu tien nhieu case
    - Go 'quit' hoac 'exit' de thoat
    - Go 'mode' de xem mode hien tai
    - Go 'help' de xem huong dan
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

from .analyzer import AIAnalyzerFactory
from .prioritizer import EmergencyPrioritizer, extract_coordinates
from .schemas import AIAnalysis, PriorityReport


# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------
class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Color for priority level
# ---------------------------------------------------------------------------
_LEVEL_COLORS = {
    "CRITICAL": C.RED,
    "HIGH": C.YELLOW,
    "MEDIUM": C.CYAN,
    "LOW": C.DIM,
}


def _print_banner(mode: str) -> None:
    print()
    print(f"{C.CYAN}{'=' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  SOSFlow AI - Emergency Analysis Terminal{C.RESET}")
    print(f"{C.DIM}  Mode: {mode}{C.RESET}")
    print(f"{C.DIM}  Commands: quit | mode | compare | help{C.RESET}")
    print(f"{C.CYAN}{'=' * 60}{C.RESET}")
    print()


def _print_help() -> None:
    print(f"""
{C.CYAN}Commands:{C.RESET}
  {C.BOLD}<text>{C.RESET}       Nhap bao cao khan cap de phan tich
  {C.BOLD}compare{C.RESET}     So sanh nhieu case va xep hang uu tien
  {C.BOLD}stations{C.RESET}    Hien thi danh sach tram cuu ho
  {C.BOLD}mode{C.RESET}        Xem mode hien tai
  {C.BOLD}help{C.RESET}        Hien thi huong dan
  {C.BOLD}quit{C.RESET}        Thoat
""")


def _print_result(analysis: AIAnalysis, elapsed: float, label: str = "") -> None:
    """In ket qua phan tich ra terminal."""
    header = "Ket qua phan tich"
    if label:
        header = f"[{label}] {header}"

    print()
    print(f"{C.GREEN}{'-' * 55}{C.RESET}")
    print(f"{C.BOLD}  {header}{C.RESET}  {C.DIM}({elapsed:.2f}s){C.RESET}")
    print(f"{C.GREEN}{'-' * 55}{C.RESET}")

    d = analysis.model_dump()

    loc = d.pop("extracted_location", {})
    loc_display = loc.get("raw_text") or "N/A"
    for part in ["province", "district", "commune", "village"]:
        if loc.get(part):
            loc_display += f" | {part}: {loc[part]}"

    fields = [
        ("Summary", d.get("summary")),
        ("Normalized", d.get("normalized_message")),
        ("Location", loc_display),
        ("People", d.get("number_of_people")),
        ("Children", d.get("number_of_children")),
        ("Elderly", d.get("number_of_elderly")),
        ("Injured", d.get("number_of_injured")),
        ("Trapped", d.get("is_trapped")),
        ("Water Level", d.get("water_level")),
        ("Needs", d.get("needs")),
        ("Risks", d.get("detected_risks")),
        ("Missing Info", d.get("missing_information")),
        ("Confidence", d.get("confidence")),
        ("Explanation", d.get("explanation")),
    ]

    for label_name, value in fields:
        if value is None:
            value_str = f"{C.DIM}null{C.RESET}"
        elif isinstance(value, list):
            value_str = ", ".join(str(v) for v in value) if value else f"{C.DIM}[]{C.RESET}"
        elif isinstance(value, bool):
            value_str = f"{C.YELLOW}{value}{C.RESET}"
        elif isinstance(value, float):
            value_str = f"{value:.2f}"
        else:
            value_str = str(value)
        print(f"  {C.CYAN}{label_name:>14}{C.RESET}  {value_str}")

    print(f"{C.GREEN}{'-' * 55}{C.RESET}")


def _print_priority_report(report: PriorityReport, elapsed: float) -> None:
    """In bao cao uu tien ra terminal."""
    print()
    print(f"{C.MAGENTA}{'=' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.MAGENTA}  BAO CAO UU TIEN CUU HO{C.RESET}  {C.DIM}({elapsed:.2f}s){C.RESET}")
    print(f"{C.MAGENTA}{'=' * 60}{C.RESET}")
    print()

    for rank, case in enumerate(report.cases, start=1):
        level_color = _LEVEL_COLORS.get(case.priority_level, C.DIM)

        # Score + distance display
        dist_info = ""
        if case.distance_km is not None and case.nearest_station:
            dist_info = f" | {case.distance_km:.1f}km -> {case.nearest_station}"

        print(f"  {C.BOLD}#{rank}{C.RESET}  "
              f"{level_color}[{case.priority_level}]{C.RESET}  "
              f"{C.BOLD}{case.case_id}{C.RESET}  "
              f"{C.DIM}(score: {case.priority_score}{dist_info}){C.RESET}")

        # Summary from original analysis
        print(f"      Summary : {case.original_analysis.summary}")

        # Coordinates
        loc = case.original_analysis.extracted_location
        if loc.latitude is not None and loc.longitude is not None:
            print(f"      Toa do  : {loc.latitude}, {loc.longitude}")

        # Key facts
        facts = []
        a = case.original_analysis
        if a.number_of_people is not None:
            facts.append(f"{a.number_of_people} nguoi")
        if a.number_of_injured:
            facts.append(f"{a.number_of_injured} bi thuong")
        if a.number_of_children:
            facts.append(f"{a.number_of_children} tre em")
        if a.number_of_elderly:
            facts.append(f"{a.number_of_elderly} nguoi gia")
        if a.is_trapped:
            facts.append("MAC KET")
        if a.water_level:
            facts.append(f"nuoc {a.water_level}m")
        if facts:
            print(f"      Facts   : {', '.join(facts)}")

        # Reasoning (wrap long text)
        reasoning = case.reasoning
        if len(reasoning) > 80:
            # Simple word wrap
            words = reasoning.split()
            lines = []
            current = ""
            for word in words:
                if len(current) + len(word) + 1 > 76:
                    lines.append(current)
                    current = word
                else:
                    current = f"{current} {word}" if current else word
            if current:
                lines.append(current)
            print(f"      Ly do   : {lines[0]}")
            for line in lines[1:]:
                print(f"                {line}")
        else:
            print(f"      Ly do   : {reasoning}")
        print()

    # Overall summary
    print(f"  {C.MAGENTA}{'-' * 56}{C.RESET}")
    summary = report.overall_summary
    if len(summary) > 80:
        words = summary.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > 72:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            lines.append(current)
        print(f"  {C.BOLD}Tong ket:{C.RESET} {lines[0]}")
        for line in lines[1:]:
            print(f"           {line}")
    else:
        print(f"  {C.BOLD}Tong ket:{C.RESET} {summary}")

    print(f"{C.MAGENTA}{'=' * 60}{C.RESET}")
    print()


# ---------------------------------------------------------------------------
# Compare mode: nhap nhieu case roi so sanh
# ---------------------------------------------------------------------------
async def compare_mode(analyzer: object, prioritizer_mode: str) -> None:
    """Che do so sanh nhieu case."""
    print(f"""
{C.MAGENTA}{'=' * 60}{C.RESET}
{C.BOLD}{C.MAGENTA}  CHE DO SO SANH UU TIEN{C.RESET}
{C.DIM}  Nhap tung bao cao, moi bao cao 1 dong.
  Them toa do: bao cao @lat,lon (VD: 10 nguoi mac ket @15.02,108.04)
  Go 'done' khi da nhap het de bat dau so sanh.
  Go 'cancel' de huy.{C.RESET}
{C.MAGENTA}{'=' * 60}{C.RESET}
""")

    cases: dict[str, AIAnalysis] = {}
    case_num = 0

    while True:
        case_num += 1
        try:
            user_input = input(
                f"{C.BOLD}  Case #{case_num}:{C.RESET} "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}  Cancelled.{C.RESET}")
            return

        if not user_input:
            case_num -= 1
            continue

        if user_input.lower() == "cancel":
            print(f"{C.DIM}  Cancelled.{C.RESET}")
            return

        if user_input.lower() == "done":
            case_num -= 1
            break

        # Extract coordinates from input (e.g. "bao cao @15.02,108.04")
        lat, lon, clean_text = extract_coordinates(user_input)

        # Analyze this case
        t0 = time.monotonic()
        try:
            result = await analyzer.analyze(clean_text)
            # Inject coordinates into analysis if found
            if lat is not None and lon is not None:
                result.extracted_location.latitude = lat
                result.extracted_location.longitude = lon
            elapsed = time.monotonic() - t0
            case_id = f"Case_{case_num}"
            cases[case_id] = result
            _print_result(result, elapsed, label=case_id)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(f"\n{C.RED}  [X] Error ({elapsed:.2f}s): {exc}{C.RESET}\n")
            case_num -= 1

    if len(cases) < 2:
        print(f"{C.YELLOW}  Can it nhat 2 case de so sanh.{C.RESET}\n")
        return

    # Prioritize
    print(f"\n{C.DIM}  Dang so sanh {len(cases)} case...{C.RESET}")
    prioritizer = EmergencyPrioritizer(mode=prioritizer_mode)

    t0 = time.monotonic()
    try:
        report = await prioritizer.prioritize(cases)
        elapsed = time.monotonic() - t0
        _print_priority_report(report, elapsed)
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"\n{C.RED}  [X] Priority error ({elapsed:.2f}s): {exc}{C.RESET}\n")


# ---------------------------------------------------------------------------
# Main interactive loop
# ---------------------------------------------------------------------------
async def interactive_loop(mode: str) -> None:
    """Vong lap interactive."""
    _print_banner(mode)

    analyzer = AIAnalyzerFactory.create(mode)
    print(f"{C.DIM}  Analyzer ready: {type(analyzer).__name__}{C.RESET}")
    print()

    # Priority mode matches AI mode
    priority_mode = "bedrock" if mode in {"bedrock", "hybrid"} else "rule"

    while True:
        try:
            user_input = input(f"{C.BOLD}> Nhap bao cao:{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}Bye!{C.RESET}")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in {"quit", "exit", "q"}:
            print(f"{C.DIM}Bye!{C.RESET}")
            break

        if cmd == "mode":
            print(f"{C.DIM}  Current mode: {mode} | Priority: {priority_mode}{C.RESET}")
            continue

        if cmd == "stations":
            from .prioritizer import DEFAULT_RESCUE_STATIONS
            print(f"\n{C.CYAN}  Tram cuu ho:{C.RESET}")
            for s in DEFAULT_RESCUE_STATIONS:
                print(f"    [{s.station_type:>7}] {s.name}  ({s.latitude}, {s.longitude})")
            print()
            continue

        if cmd == "help":
            _print_help()
            continue

        if cmd == "compare":
            await compare_mode(analyzer, priority_mode)
            continue

        # Single case analysis
        t0 = time.monotonic()
        try:
            result = await analyzer.analyze(user_input)
            elapsed = time.monotonic() - t0
            _print_result(result, elapsed)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(f"\n{C.RED}  [X] Error ({elapsed:.2f}s): {exc}{C.RESET}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SOSFlow AI - Interactive emergency analysis terminal",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["bedrock", "hybrid", "mock"],
        default=os.getenv("AI_PROVIDER", os.getenv("SOSFLOW_AI_MODE", "bedrock")),
        help="AI mode (default: bedrock)",
    )
    args = parser.parse_args()

    asyncio.run(interactive_loop(args.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
