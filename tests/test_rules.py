import pytest

from quiz_platform.question_bank import (
    AllOfRule,
    FormatRule,
    ReuseCooldownRule,
    TopicRule,
    build_candidate_pool,
    import_questions,
)


def test_leaf_rule_has_a_fixed_reason():
    rule = TopicRule(["testing"])

    assert rule.exclusion_reason({"topic": "maintenance"}) == "topic"
    assert rule.exclusion_reason({"topic": "testing"}) is None


def test_nested_composite_returns_first_declared_exclusion():
    rule = AllOfRule(
        [
            TopicRule(["testing"]),
            AllOfRule([FormatRule(["short_answer"])]),
        ]
    )

    assert rule.exclusion_reason({"topic": "testing", "format": "code_reading"}) == "format"
    assert rule.exclusion_reason({"topic": "testing", "format": "short_answer"}) is None


def test_nested_composite_renders_as_one_equation():
    rule = AllOfRule(
        [
            TopicRule(["testing"]),
            AllOfRule([FormatRule(["short_answer"])]),
        ]
    )

    assert rule.render() == "(topic IN {testing} AND (format IN {short_answer}))"


def test_reuse_cooldown_has_an_exact_inclusive_boundary():
    rule = ReuseCooldownRule("2026-09-25", 30)

    assert rule.exclusion_reason({"last_used": "2026-08-27"}) == "reuse"
    assert rule.exclusion_reason({"last_used": "2026-08-26"}) is None
    assert rule.exclusion_reason({"last_used": None}) is None


@pytest.mark.parametrize("cooldown", [-1, "30"])
def test_reuse_cooldown_rejects_invalid_values(cooldown):
    with pytest.raises(ValueError):
        ReuseCooldownRule("2026-09-25", cooldown)


def test_positive_cooldown_requires_a_reference_date():
    with pytest.raises(ValueError, match="reference_date"):
        build_candidate_pool([], {"reuse_cooldown_days": 1})


def test_candidate_pool_integrates_reuse_reporting(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(
        """[
          {"id":"Q-1","text":"Recent","format":"short_answer","topic":"testing",
           "difficulty":1,"learning_outcomes":["LO1"],"status":"approved",
           "estimated_minutes":2,"tags":[],"last_used":"2026-09-12"},
          {"id":"Q-2","text":"Older","format":"short_answer","topic":"testing",
           "difficulty":1,"learning_outcomes":["LO1"],"status":"approved",
           "estimated_minutes":2,"tags":[],"last_used":"2026-08-12"}
        ]""",
        encoding="utf-8",
    )
    questions, _report = import_questions(str(path))

    eligible, report = build_candidate_pool(
        questions,
        {"required_status": "approved", "reuse_cooldown_days": 30},
        reference_date="2026-09-25",
    )

    assert [question["id"] for question in eligible] == ["Q-2"]
    assert report["excluded_by_reuse"] == ["Q-1"]
    assert report["rule_expression"] == (
        "(status = approved AND "
        "(last_used IS NULL OR days_since(last_used, 2026-09-25) >= 30))"
    )
