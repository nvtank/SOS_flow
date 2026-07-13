from pathlib import Path

from app.services.priority_engine import PriorityEngine, PriorityInput


RULES_PATH = Path(__file__).resolve().parents[2] / "config" / "priority-rules.yaml"


def test_priority_engine_marks_life_threatening_case_as_critical():
    engine = PriorityEngine(RULES_PATH)
    result = engine.calculate(
        PriorityInput(
            message="Sắp chết rồi, có người không thở được, nước cuốn rất mạnh.",
            number_of_people=6,
            number_of_children=1,
            number_of_injured=2,
            is_trapped=True,
            water_level=3.0,
        )
    )

    assert result["priority_level"] == "CRITICAL"
    assert result["priority_score"] >= 70
    assert any("nguy hiểm" in reason for reason in result["reasons"])


def test_priority_engine_keeps_safe_low_water_case_low():
    engine = PriorityEngine(RULES_PATH)
    result = engine.calculate(PriorityInput(message="Nhà tôi bị ngập nhưng mọi người vẫn an toàn.", number_of_people=1, water_level=0.2))

    assert result["priority_level"] == "LOW"
    assert result["priority_score"] < 30
