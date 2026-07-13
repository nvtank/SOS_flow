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


def test_single_life_threatening_phrase_gets_critical_safety_floor_without_ai():
    engine = PriorityEngine(RULES_PATH)
    result = engine.calculate(PriorityInput(message="Cứu với, có người sắp chết rồi.", number_of_people=1))

    assert result["priority_level"] == "CRITICAL"
    assert result["priority_score"] == 100
    assert any("đe dọa tính mạng" in reason for reason in result["reasons"])


def test_unaccented_breathing_emergency_gets_critical_safety_floor():
    engine = PriorityEngine(RULES_PATH)
    result = engine.calculate(PriorityInput(message="Cuu toi, co nguoi khong tho duoc", number_of_people=1))

    assert result["priority_level"] == "CRITICAL"
    assert result["priority_score"] == 100


def test_priority_engine_keeps_safe_low_water_case_low():
    engine = PriorityEngine(RULES_PATH)
    result = engine.calculate(PriorityInput(message="Nhà tôi bị ngập nhưng mọi người vẫn an toàn.", number_of_people=1, water_level=0.2))

    assert result["priority_level"] == "LOW"
    assert result["priority_score"] < 30


def test_priority_engine_escalates_imminent_survival_language():
    engine = PriorityEngine(RULES_PATH)
    result = engine.calculate(
        PriorityInput(
            message="Tôi không trụ nổi, dự kiến không sống qua 9 giờ vì nước dâng quá cao.",
            number_of_people=2,
            number_of_elderly=1,
            is_trapped=True,
        )
    )

    assert result["priority_level"] == "CRITICAL"
    assert any("không thể cầm cự" in reason for reason in result["reasons"])
