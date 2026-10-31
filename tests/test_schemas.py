"""Unit tests validating core data contracts in app.schemas."""

import pytest
from app.schemas import (
    Operator,
    Field_,
    AudienceType,
    VerdictStatus,
    Clause,
    Condition,
    Benefit,
    Obligation,
    Scheme,
    UserProfile,
    Reason,
    Verdict,
    Segment,
    Explainer,
    InterviewQuestion,
    TraceEntry,
)


def test_clause_schema():
    clause = Clause(
        id="doc1-p1-c1",
        doc_id="sha256_mock_hash",
        page=1,
        text="Farmers possessing land up to 2 hectares are eligible for financial assistance.",
    )
    assert clause.id == "doc1-p1-c1"
    assert clause.page == 1


def test_condition_cited_contract():
    cond = Condition(
        clause_id="doc1-p1-c1",
        quote="land up to 2 hectares",
        field=Field_.LAND_HECTARES,
        operator=Operator.LTE,
        value=2.0,
        unit="hectares",
    )
    assert cond.clause_id == "doc1-p1-c1"
    assert cond.field == Field_.LAND_HECTARES
    assert cond.value == 2.0


def test_scheme_model_construction():
    scheme = Scheme(
        doc_id="doc1",
        title="PM Kisan Samman Nidhi",
        audience=AudienceType.CITIZEN,
        summary="Income support scheme for farmers.",
        benefits=[
            Benefit(
                clause_id="doc1-p1-c2",
                quote="financial benefit of Rs 6000 per year",
                description="Annual financial assistance",
                amount=6000.0,
                frequency="yearly",
            )
        ],
        conditions=[
            Condition(
                clause_id="doc1-p1-c1",
                quote="land up to 2 hectares",
                field=Field_.LAND_HECTARES,
                operator=Operator.LTE,
                value=2.0,
                unit="hectares",
            )
        ],
        obligations=[
            Obligation(
                clause_id="doc1-p1-c3",
                quote="must submit Aadhaar and land record",
                description="Submit identification and land ownership records",
                required_documents=["Aadhaar Card", "Land Ownership Record"],
                deadline="31 March",
            )
        ],
    )
    assert len(scheme.benefits) == 1
    assert len(scheme.conditions) == 1
    assert len(scheme.obligations) == 1
    assert scheme.benefits[0].amount == 6000.0


def test_verdict_and_user_profile():
    profile = UserProfile(answers={Field_.LAND_HECTARES: 1.5, Field_.ANNUAL_INCOME: 120000})
    assert profile.get(Field_.LAND_HECTARES) == 1.5
    assert Field_.LAND_HECTARES in profile

    cond = Condition(
        clause_id="doc1-p1-c1",
        quote="land up to 2 hectares",
        field=Field_.LAND_HECTARES,
        operator=Operator.LTE,
        value=2.0,
    )
    reason = Reason(condition=cond, passed=True, explanation="1.5 <= 2.0")
    verdict = Verdict(
        status=VerdictStatus.YES,
        reasons=[reason],
        missing_fields=[],
        summary="Eligible for scheme benefits.",
    )
    assert verdict.status == VerdictStatus.YES
    assert verdict.reasons[0].passed is True


def test_explainer_segments():
    segment = Segment(
        text="आप इस योजना के लिए पात्र हैं।",
        clause_ids=["doc1-p1-c1"],
    )
    explainer = Explainer(
        language="hi",
        segments=[segment],
        checklist=["आधार कार्ड", "भूमि दस्तावेज"],
    )
    assert explainer.language == "hi"
    assert len(explainer.segments) == 1
    assert explainer.segments[0].clause_ids == ["doc1-p1-c1"]

