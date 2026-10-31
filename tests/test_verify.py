"""Unit tests for the self-correcting verification engine."""

import pytest
from app.nodes.verify import (
    check_quote_substring,
    check_value_in_quote,
    normalize_text,
    parse_indian_numbers,
    verify_scheme,
)
from app.schemas import (
    AudienceType,
    Benefit,
    Clause,
    Condition,
    Field_,
    Obligation,
    Operator,
    Scheme,
)


def test_normalize_text():
    raw = "  ‘Farmers’ with   2.0 \n Hectares — eligible…  "
    normalized = normalize_text(raw)
    assert "farmers" in normalized
    assert "  " not in normalized


def test_parse_indian_numbers():
    text1 = "Total annual income must not exceed 1.5 lakh or 2 Lakhs."
    nums1 = parse_indian_numbers(text1)
    assert 150000.0 in nums1
    assert 200000.0 in nums1

    text2 = "Under the scheme, Rs. 6,000/- is credited directly. Maximum loan up to 2 crore."
    nums2 = parse_indian_numbers(text2)
    assert 6000.0 in nums2
    assert 20000000.0 in nums2

    text3 = "Cultivable landholding up to 2.5 hectares."
    nums3 = parse_indian_numbers(text3)
    assert 2.5 in nums3


def test_check_quote_substring_genuine_and_fake():
    clause = Clause(
        id="pmk-p1-c01",
        doc_id="doc1",
        page=1,
        text="All landholder farmer families having cultivable landholding up to 2 hectares are eligible.",
    )
    clauses_dict = {clause.id: clause}

    # Genuine quote
    good_cond = Condition(
        clause_id=clause.id,
        quote="landholding up to 2 hectares",
        field=Field_.LAND_HECTARES,
        operator=Operator.LTE,
        value=2.0,
    )
    assert check_quote_substring(good_cond, clauses_dict) is True

    # Corrupted / hallucinated quote
    bad_cond = Condition(
        clause_id=clause.id,
        quote="farmers with 50 acres of free land",
        field=Field_.LAND_HECTARES,
        operator=Operator.LTE,
        value=50.0,
    )
    assert check_quote_substring(bad_cond, clauses_dict) is False


def test_check_value_in_quote_catches_planted_wrong_number():
    cond_good = Condition(
        clause_id="c1",
        quote="income less than 1.5 lakh per annum",
        field=Field_.ANNUAL_INCOME,
        operator=Operator.LT,
        value=150000.0,
    )
    assert check_value_in_quote(cond_good, cond_good.quote) is True

    # Planted corrupted value (quote says 1.5 lakh, value claims 500000)
    cond_bad = Condition(
        clause_id="c1",
        quote="income less than 1.5 lakh per annum",
        field=Field_.ANNUAL_INCOME,
        operator=Operator.LT,
        value=500000.0,
    )
    assert check_value_in_quote(cond_bad, cond_bad.quote) is False


@pytest.mark.asyncio
async def test_verify_scheme_catches_corrupted_extractions():
    clause1 = Clause(
        id="pmk-p1-c01",
        doc_id="doc1",
        page=1,
        text="Small farmers with cultivable landholding up to 2 hectares shall receive assistance.",
    )
    clause2 = Clause(
        id="pmk-p1-c02",
        doc_id="doc1",
        page=1,
        text="Financial grant of Rs. 6000 per year will be provided in three equal installments.",
    )
    clauses = [clause1, clause2]

    # Valid condition and benefit
    valid_cond = Condition(
        clause_id=clause1.id,
        quote="landholding up to 2 hectares",
        field=Field_.LAND_HECTARES,
        operator=Operator.LTE,
        value=2.0,
    )
    valid_benefit = Benefit(
        clause_id=clause2.id,
        quote="Rs. 6000 per year",
        description="Annual direct transfer",
        amount=6000.0,
        frequency="yearly",
    )

    # Deliberately planted corrupted condition (quote does not exist in clause 1)
    planted_bad_cond = Condition(
        clause_id=clause1.id,
        quote="annual turnover greater than 50 crore",
        field=Field_.ANNUAL_TURNOVER,
        operator=Operator.GT,
        value=500000000.0,
    )

    unverified_scheme = Scheme(
        doc_id="doc1",
        title="PM Kisan Scheme",
        audience=AudienceType.CITIZEN,
        benefits=[valid_benefit],
        conditions=[valid_cond, planted_bad_cond],
        obligations=[],
        uncertain=[],
        confidence=1.0,
    )

    verified = await verify_scheme(unverified_scheme, clauses, llm=None)

    # Corrupted condition must be removed from verified conditions
    assert len(verified.conditions) == 1
    assert verified.conditions[0].field == Field_.LAND_HECTARES

    # Must be logged in uncertain list
    assert len(verified.uncertain) >= 1
    assert any("annual_turnover" in u for u in verified.uncertain)

    # Benefit preserved
    assert len(verified.benefits) == 1
    assert verified.benefits[0].amount == 6000.0

    # Confidence score reflects 2 passed out of 3 total items (0.67)
    assert verified.confidence == 0.67

