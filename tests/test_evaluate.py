"""Unit tests for the pure Python deterministic rule engine."""

from app.nodes.evaluate import evaluate, normalize_units
from app.schemas import (
    AudienceType,
    Condition,
    Field_,
    Operator,
    Scheme,
    UserProfile,
    VerdictStatus,
)


def test_normalize_units():
    # Acres to hectares: 5 acres * 0.404686 = 2.0234 ha
    assert normalize_units(5.0, from_unit="acres", to_unit="hectares") == 2.0234
    # Hectares to acres: 2 ha * 2.47105 = 4.9421 acres
    assert normalize_units(2.0, from_unit="ha", to_unit="acres") == 4.9421
    # Lakh to INR
    assert normalize_units(1.5, from_unit="lakh", to_unit="inr") == 150000.0
    # Crore to INR
    assert normalize_units(2.0, from_unit="crore", to_unit="inr") == 20000000.0


def test_all_operators_and_boundary_values():
    # Boundary value test: limit is 2.0
    c_lte = Condition(clause_id="c1", quote="q", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0)
    c_lt = Condition(clause_id="c1", quote="q", field=Field_.LAND_HECTARES, operator=Operator.LT, value=2.0)
    c_gte = Condition(clause_id="c2", quote="q", field=Field_.AGE, operator=Operator.GTE, value=18)
    c_gt = Condition(clause_id="c2", quote="q", field=Field_.AGE, operator=Operator.GT, value=18)
    c_eq = Condition(clause_id="c3", quote="q", field=Field_.CATEGORY, operator=Operator.EQ, value="OBC")
    c_neq = Condition(clause_id="c4", quote="q", field=Field_.CATEGORY, operator=Operator.NEQ, value="General")
    c_in = Condition(clause_id="c5", quote="q", field=Field_.STATE, operator=Operator.IN, value=["Maharashtra", "Gujarat"])
    c_notin = Condition(clause_id="c6", quote="q", field=Field_.STATE, operator=Operator.NOT_IN, value=["Delhi"])

    # 1. Boundary: land == 2.0 (should pass LTE, fail LT)
    scheme_lte = Scheme(doc_id="d1", title="S", conditions=[c_lte])
    scheme_lt = Scheme(doc_id="d1", title="S", conditions=[c_lt])
    p_exact_2 = UserProfile(answers={Field_.LAND_HECTARES: 2.0})

    assert evaluate(scheme_lte, p_exact_2).status == VerdictStatus.YES
    assert evaluate(scheme_lt, p_exact_2).status == VerdictStatus.NO

    # 2. Boundary: age == 18 (should pass GTE, fail GT)
    scheme_gte = Scheme(doc_id="d1", title="S", conditions=[c_gte])
    scheme_gt = Scheme(doc_id="d1", title="S", conditions=[c_gt])
    p_exact_18 = UserProfile(answers={Field_.AGE: 18})

    assert evaluate(scheme_gte, p_exact_18).status == VerdictStatus.YES
    assert evaluate(scheme_gt, p_exact_18).status == VerdictStatus.NO

    # 3. Categorical eq, neq, in, not_in
    p_user = UserProfile(answers={
        Field_.CATEGORY: "OBC",
        Field_.STATE: "Maharashtra",
    })
    s_cat = Scheme(doc_id="d1", title="S", conditions=[c_eq, c_neq, c_in, c_notin])
    v_cat = evaluate(s_cat, p_user)
    assert v_cat.status == VerdictStatus.YES
    assert all(r.passed is True for r in v_cat.reasons)


def test_verdict_no_when_any_condition_fails():
    c1 = Condition(clause_id="clause_land", quote="q", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0)
    c2 = Condition(clause_id="clause_income", quote="q", field=Field_.ANNUAL_INCOME, operator=Operator.LTE, value=150000)
    scheme = Scheme(doc_id="d1", title="PM Kisan", conditions=[c1, c2])

    # User passes land (1.5 <= 2.0) but fails income (200000 > 150000)
    profile = UserProfile(answers={Field_.LAND_HECTARES: 1.5, Field_.ANNUAL_INCOME: 200000})
    verdict = evaluate(scheme, profile)

    assert verdict.status == VerdictStatus.NO
    assert "clause_income" in verdict.summary
    assert verdict.reasons[0].passed is True
    assert verdict.reasons[1].passed is False


def test_verdict_maybe_when_fields_missing():
    c1 = Condition(clause_id="c1", quote="q", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0)
    c2 = Condition(clause_id="c2", quote="q", field=Field_.ANNUAL_INCOME, operator=Operator.LTE, value=150000)
    scheme = Scheme(doc_id="d1", title="Scheme", conditions=[c1, c2])

    # User only answers land, skips income
    profile = UserProfile(answers={Field_.LAND_HECTARES: 1.0})
    verdict = evaluate(scheme, profile)

    assert verdict.status == VerdictStatus.MAYBE
    assert Field_.ANNUAL_INCOME in verdict.missing_fields
    assert len(verdict.missing_fields) == 1


def test_verdict_maybe_when_scheme_has_uncertain_clauses():
    c1 = Condition(clause_id="c1", quote="q", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0)
    scheme = Scheme(
        doc_id="d1",
        title="Scheme",
        conditions=[c1],
        uncertain=["Clause 5 mentions institutional landholder exclusion which requires land deed check."],
    )

    profile = UserProfile(answers={Field_.LAND_HECTARES: 1.5})
    verdict = evaluate(scheme, profile)

    # Condition passed, but because uncertain clauses exist, overall status is MAYBE
    assert verdict.status == VerdictStatus.MAYBE
    assert "ambiguous/unverified" in verdict.summary


def test_evaluate_with_unit_conversion():
    # Condition in hectares (<= 2.0 ha)
    c1 = Condition(clause_id="c1", quote="q", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0, unit="hectares")
    scheme = Scheme(doc_id="d1", title="Scheme", conditions=[c1])

    # User answered in acres: 3 acres (~1.214 hectares -> passes <= 2.0)
    profile = UserProfile(answers={Field_.LAND_HECTARES: 3.0})
    user_units = {Field_.LAND_HECTARES: "acres"}

    verdict = evaluate(scheme, profile, user_units=user_units)
    assert verdict.status == VerdictStatus.YES
    assert verdict.reasons[0].passed is True

    # User answered 6 acres (~2.428 hectares -> fails <= 2.0)
    profile_large = UserProfile(answers={Field_.LAND_HECTARES: 6.0})
    verdict_fail = evaluate(scheme, profile_large, user_units=user_units)
    assert verdict_fail.status == VerdictStatus.NO
    assert verdict_fail.reasons[0].passed is False

