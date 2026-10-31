"""Unit tests for interview generation and answer validation."""

from app.nodes.interview import generate_interview_questions, validate_answer
from app.schemas import (
    Condition,
    Field_,
    Operator,
    Scheme,
    UserProfile,
)


def test_generate_interview_questions_minimal_and_skips_answered():
    cond1 = Condition(clause_id="c1", quote="q1", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0)
    cond2 = Condition(clause_id="c2", quote="q2", field=Field_.ANNUAL_INCOME, operator=Operator.LT, value=150000)
    cond3 = Condition(clause_id="c3", quote="q3", field=Field_.AGE, operator=Operator.GTE, value=18)
    scheme = Scheme(doc_id="d1", title="Scheme", conditions=[cond1, cond2, cond3])

    # User already answered AGE
    profile = UserProfile(answers={Field_.AGE: 25})

    questions = generate_interview_questions(scheme, profile, language="en")

    # Should ask only for LAND_HECTARES and ANNUAL_INCOME
    assert len(questions) == 2
    asked_fields = [q.field for q in questions]
    assert Field_.LAND_HECTARES in asked_fields
    assert Field_.ANNUAL_INCOME in asked_fields
    assert Field_.AGE not in asked_fields


def test_validate_answer_number_and_ranges():
    # Valid number
    valid, val, err = validate_answer(Field_.ANNUAL_INCOME, "1,50,000")
    assert valid is True
    assert val == 150000.0
    assert err is None

    # Invalid string
    valid, val, err = validate_answer(Field_.AGE, "not_a_number")
    assert valid is False
    assert err is not None

    # Out of bounds
    valid, val, err = validate_answer(Field_.AGE, "-5")
    assert valid is False
    assert "at least" in err.lower()


def test_validate_answer_boolean_and_hindi():
    valid, val, _ = validate_answer(Field_.IS_FARMER, "yes")
    assert valid is True and val is True

    valid, val, _ = validate_answer(Field_.IS_FARMER, "हाँ")
    assert valid is True and val is True

    valid, val, _ = validate_answer(Field_.IS_FARMER, "no")
    assert valid is True and val is False

    valid, val, _ = validate_answer(Field_.IS_FARMER, "नहीं")
    assert valid is True and val is False


def test_validate_answer_choice():
    valid, val, _ = validate_answer(Field_.CATEGORY, "obc")
    assert valid is True
    assert val == "OBC"

    valid, _, err = validate_answer(Field_.CATEGORY, "InvalidCategory")
    assert valid is False
    assert "allowed options" in err

