"""Unit tests for the structured extraction node."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.nodes.extract import extract_scheme, group_clauses
from app.schemas import (
    AudienceType,
    Benefit,
    Clause,
    Condition,
    Field_,
    Operator,
    SectionExtraction,
)


def test_group_clauses_splits_by_character_limit():
    clauses = [
        Clause(id="c1", doc_id="d1", page=1, text="A" * 600),
        Clause(id="c2", doc_id="d1", page=1, text="B" * 600),
        Clause(id="c3", doc_id="d1", page=1, text="C" * 600),
        Clause(id="c4", doc_id="d1", page=1, text="D" * 600),
    ]

    # Limit to 1000 characters per section
    groups = group_clauses(clauses, max_chars=1000)
    assert len(groups) >= 2
    for g in groups:
        total_len = sum(len(c.text) for c in g)
        assert total_len <= 1200


@pytest.mark.asyncio
async def test_extract_scheme_end_to_end_with_verification():
    clause1 = Clause(
        id="c1",
        doc_id="d1",
        page=1,
        text="Small farmers with cultivable landholding up to 2 hectares are eligible for income assistance.",
    )
    clause2 = Clause(
        id="c2",
        doc_id="d1",
        page=1,
        text="A financial grant of Rs. 6000 per year will be deposited in bank accounts.",
    )
    clauses = [clause1, clause2]

    mock_llm = MagicMock()
    mock_extraction = SectionExtraction(
        title="PM Kisan Scheme",
        audience=AudienceType.CITIZEN,
        conditions=[
            Condition(
                clause_id="c1",
                quote="landholding up to 2 hectares",
                field=Field_.LAND_HECTARES,
                operator=Operator.LTE,
                value=2.0,
            )
        ],
        benefits=[
            Benefit(
                clause_id="c2",
                quote="Rs. 6000 per year",
                description="Annual financial grant",
                amount=6000.0,
                frequency="yearly",
            )
        ],
        obligations=[],
        uncertain=["Aadhaar seeding is subject to bank verification rules."],
    )

    mock_llm.generate_structured = AsyncMock(return_value=mock_extraction)

    scheme = await extract_scheme(clauses, "d1", mock_llm, verify=True)

    assert scheme.title == "PM Kisan Scheme"
    assert scheme.audience == AudienceType.CITIZEN
    assert len(scheme.conditions) == 1
    assert scheme.conditions[0].field == Field_.LAND_HECTARES
    assert len(scheme.benefits) == 1
    assert scheme.benefits[0].amount == 6000.0
    assert len(scheme.uncertain) == 1
    assert scheme.confidence == 1.0

