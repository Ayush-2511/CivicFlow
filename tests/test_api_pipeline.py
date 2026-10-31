"""Integration tests for Phase 7: LangGraph wiring, API endpoints, and resume flow."""

import asyncio
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    AudienceType,
    Benefit,
    Condition,
    Explainer,
    Field_,
    Operator,
    SectionExtraction,
    Segment,
    VerificationResult,
    VerdictStatus,
)

client = TestClient(app)


def test_verified_sources_endpoint():
    response = client.get("/sources/verified")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert "url" in data[0]


def test_typed_exception_handler():
    from app.exceptions import UnreadableDocument

    # Manually trigger an unreadable document exception to verify JSON contract
    @app.get("/test/trigger-unreadable")
    def trigger():
        raise UnreadableDocument("Image is blurry.")

    response = client.get("/test/trigger-unreadable")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "UnreadableDocument"
    assert "suggestion" in data


@pytest.mark.asyncio
async def test_full_pipeline_api_flow_mock_llm():
    """Verify complete graph flow end-to-end: ingest → parse → index → extract → verify →
    interview (interrupt) → resume → evaluate → compose → voice.

    Drives the graph directly (not via HTTP background task) so that mocks
    remain in-scope for the entire async execution.
    """
    import uuid
    from langgraph.types import Command
    from app.graph import build_graph
    from app.schemas import VerificationResult, VerdictStatus
    from langgraph.checkpoint.memory import MemorySaver

    sample_text = (
        "1. Short Title: PM Kisan Scheme.\n"
        "2. Eligibility: Farmers with cultivable land up to 2 hectares.\n"
        "3. Financial Benefit: Rs. 6000 per year."
    )

    mock_explainer = Explainer(
        language="hi",
        segments=[
            Segment(text="आप पात्र हैं।", clause_ids=["c1"]),
            Segment(text="₹6000 मिलेंगे।", clause_ids=["c1"]),
        ],
        checklist=["आधार कार्ड"],
    )

    async def mock_gen_structured(prompt, schema, *args, **kwargs):
        import re
        if schema == SectionExtraction:
            # Find all clause IDs from the prompt; pick the one whose line contains the relevant quote
            all_ids = re.findall(r"\[CLAUSE_ID: ([^\]]+)\]", prompt)
            # Find the clause block that has the eligibility text
            eligibility_id = all_ids[0] if all_ids else "c1"
            benefit_id = all_ids[0] if all_ids else "c1"
            for cid in all_ids:
                # Grab the text block after this clause_id header
                pattern = rf"\[CLAUSE_ID: {re.escape(cid)}\][^\[]*"
                m = re.search(pattern, prompt, re.DOTALL)
                block = m.group(0) if m else ""
                if "cultivable land" in block.lower():
                    eligibility_id = cid
                if "6000" in block or "rs." in block.lower():
                    benefit_id = cid
            return SectionExtraction(
                title="PM Kisan Scheme",
                audience=AudienceType.CITIZEN,
                conditions=[
                    Condition(
                        clause_id=eligibility_id,
                        quote="cultivable land up to 2 hectares",
                        field=Field_.LAND_HECTARES,
                        operator=Operator.LTE,
                        value=2.0,
                    )
                ],
                benefits=[
                    Benefit(
                        clause_id=benefit_id,
                        quote="Rs. 6000 per year",
                        description="Annual direct transfer",
                        amount=6000.0,
                    )
                ],
                obligations=[],
                uncertain=[],
            )
        if schema == Explainer:
            return mock_explainer
        if schema == VerificationResult:
            return VerificationResult(is_supported=True, reason="Quote found verbatim.")
        return None

    mock_llm = MagicMock()
    mock_llm.generate_structured = AsyncMock(side_effect=mock_gen_structured)

    mock_tts = MagicMock()
    mock_tts.synthesize = AsyncMock(return_value=b"ID3" + b"\x00" * 200)

    with patch("app.graph.get_llm", return_value=mock_llm), \
         patch("app.graph.get_tts", return_value=mock_tts):

        # Build a fresh graph with its own MemorySaver so we don't pollute other tests
        test_graph = build_graph()
        run_id = f"test_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": run_id}}

        initial_state = {
            "run_id": run_id,
            "file_bytes": sample_text.encode("utf-8"),
            "filename": "pmkisan.txt",
            "content_type": "text/plain",
            "url": None,
            "persona": "citizen",
            "language": "hi",
            "status": "started",
            "trace": [],
            "verify_retries": 0,
        }

        # --- Phase 1: stream until interrupt (interview node pauses) ---
        interrupt_value = None
        async for event in test_graph.astream(initial_state, config=config):
            for node_name, node_output in event.items():
                if "__interrupt__" in event:
                    interrupt_value = event["__interrupt__"]
                    break
            if "__interrupt__" in event:
                interrupt_value = event["__interrupt__"]
                break

        # The graph should have paused waiting for interview answers
        snap = test_graph.get_state(config)
        assert snap.next, "Graph should be paused at interview node"
        assert "interview" in snap.next

        # --- Phase 2: resume with answers ---
        resume_payload = {
            "answers": {"land_hectares": 1.5},
            "units": {"land_hectares": "hectares"},
        }
        final_state = None
        async for event in test_graph.astream(
            Command(resume=resume_payload), config=config
        ):
            for node_name, node_output in event.items():
                pass  # consume all events
            final_state = event

        # --- Assertions ---
        snap = test_graph.get_state(config)
        vals = snap.values

        assert vals.get("status") == "completed", f"Expected completed, got {vals.get('status')}: {vals.get('error')}"
        verdict = vals.get("verdict")
        assert verdict is not None, "No verdict in final state"
        assert verdict.status == VerdictStatus.YES, f"Expected YES, got {verdict.status}"
        trace = vals.get("trace", [])
        assert len(trace) >= 5, f"Expected ≥5 trace entries, got {len(trace)}"
