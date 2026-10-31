"""Unit tests for explainer composition node."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.nodes.compose import compose_explainer
from app.schemas import (
    AudienceType,
    Benefit,
    Condition,
    Explainer,
    Field_,
    Operator,
    Reason,
    Scheme,
    Segment,
    Verdict,
    VerdictStatus,
)


@pytest.mark.asyncio
async def test_compose_explainer_citizen():
    scheme = Scheme(
        doc_id="doc1",
        title="PM Kisan",
        audience=AudienceType.CITIZEN,
        benefits=[
            Benefit(clause_id="c2", quote="Rs. 6000 per year", description="Financial benefit", amount=6000.0)
        ],
        conditions=[
            Condition(clause_id="c1", quote="land up to 2 hectares", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0)
        ],
    )
    cond = scheme.conditions[0]
    verdict = Verdict(
        status=VerdictStatus.YES,
        reasons=[Reason(condition=cond, passed=True, explanation="Passed <= 2.0 ha")],
        summary="Eligible for PM Kisan.",
    )

    mock_explainer = Explainer(
        language="hi",
        segments=[
            Segment(
                text="बधाई हो, आप इस योजना के लिए पूरी तरह पात्र हैं।",
                clause_ids=["c1"],
            ),
            Segment(
                text="आपको प्रति वर्ष ₹6,000 की वित्तीय सहायता सीधे बैंक खाते में मिलेगी।",
                clause_ids=["c2"],
            ),
        ],
        checklist=["आधार कार्ड", "ज़मीन की खतौनी"],
    )

    mock_llm = MagicMock()
    mock_llm.generate_structured = AsyncMock(return_value=mock_explainer)

    explainer = await compose_explainer(
        scheme=scheme,
        verdict=verdict,
        persona=AudienceType.CITIZEN,
        language="hi",
        llm=mock_llm,
    )

    assert explainer.language == "hi"
    assert len(explainer.segments) == 2
    assert explainer.segments[0].clause_ids == ["c1"]
    assert len(explainer.checklist) == 2
    assert mock_llm.generate_structured.call_count == 1

