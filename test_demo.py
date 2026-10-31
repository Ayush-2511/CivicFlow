"""Interactive self-test script for CivicFlow.

Run with: ./.venv/Scripts/python test_demo.py
"""

import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
from app.nodes.parse import PageText
from app.nodes.index import split_into_clauses, BM25ClauseIndex
from app.nodes.verify import verify_scheme
from app.nodes.interview import generate_interview_questions, validate_answer
from app.nodes.evaluate import evaluate
from app.nodes.voice import synthesize_explainer_voice
from app.providers.speech import EdgeTTSProvider
from app.schemas import (
    AudienceType,
    Benefit,
    Clause,
    Condition,
    Explainer,
    Field_,
    Operator,
    Scheme,
    Segment,
    UserProfile,
)


def test_clause_splitting_and_bm25():
    print("=" * 65)
    print("1. CLAUSE SPLITTING & BM25 SEARCH")
    print("=" * 65)

    sample_doc = """
1. Short Title: This scheme shall be known as the PM Kisan Samman Nidhi.
2. Eligibility: All landholder farmer families having cultivable land up to 2 hectares are eligible for financial assistance.
3. Benefit Details: Financial benefit of Rs 6000 per year will be provided in three equal installments.
4. Required Documents: Beneficiaries must submit Aadhaar card, bank account details, and land revenue records.
    """

    doc_id = "sample_pmkisan_doc_2026"
    clauses = split_into_clauses([PageText(page=1, text=sample_doc.strip())], doc_id=doc_id)

    print(f"Extracted {len(clauses)} atomic clauses:\n")
    for c in clauses:
        print(f"  [{c.id}] -> {c.text}")

    print("\n--- BM25 Search Query: 'land limit 2 hectares' ---")
    index = BM25ClauseIndex(clauses)
    top_matches = index.search("land limit 2 hectares", top_k=1)
    if top_matches:
        print(f"  Top Match [{top_matches[0].id}]: {top_matches[0].text}\n")


async def test_verifier():
    print("=" * 65)
    print("2. SELF-CORRECTING VERIFIER (CATCHING A PLANTED LIE)")
    print("=" * 65)

    clause = Clause(
        id="demo-p1-c01",
        doc_id="demo1",
        page=1,
        text="Small farmers possessing agricultural land up to 2 hectares get Rs. 6,000 per year.",
    )

    # 1. Genuine condition (supported by text)
    good_cond = Condition(
        clause_id="demo-p1-c01",
        quote="land up to 2 hectares",
        field=Field_.LAND_HECTARES,
        operator=Operator.LTE,
        value=2.0,
    )

    # 2. Planted lie (fabricated turnover requirement)
    fake_cond = Condition(
        clause_id="demo-p1-c01",
        quote="annual turnover exceeding 50 crore",
        field=Field_.ANNUAL_TURNOVER,
        operator=Operator.GT,
        value=500000000.0,
    )

    scheme = Scheme(
        doc_id="demo1",
        title="Demo Scheme",
        audience=AudienceType.CITIZEN,
        conditions=[good_cond, fake_cond],
    )

    print("Before verification:")
    print("  Claimed conditions:", [c.field.value for c in scheme.conditions])

    verified = await verify_scheme(scheme, [clause], llm=None)

    print("\nAfter self-correcting verification:")
    print("  Verified conditions (Kept):", [c.field.value for c in verified.conditions])
    print("  Flagged items (Moved to uncertain):", verified.uncertain)
    print(f"  Confidence score: {verified.confidence * 100}%\n")


def test_interview_and_evaluation():
    print("=" * 65)
    print("3. DYNAMIC INTERVIEW & DETERMINISTIC RULE ENGINE")
    print("=" * 65)

    cond_land = Condition(clause_id="c1", quote="land up to 2 ha", field=Field_.LAND_HECTARES, operator=Operator.LTE, value=2.0, unit="hectares")
    cond_income = Condition(clause_id="c2", quote="income < 1.5 lakh", field=Field_.ANNUAL_INCOME, operator=Operator.LT, value=150000, unit="INR")
    scheme = Scheme(doc_id="d1", title="PM Kisan", conditions=[cond_land, cond_income])

    # Case A: User profile has no answers yet
    empty_profile = UserProfile()
    questions = generate_interview_questions(scheme, empty_profile, language="hi")
    print(f"Dynamic interview identified {len(questions)} missing field(s):")
    for q in questions:
        print(f"  - [{q.field.value}] Hindi prompt: {q.question_text}")

    # Case B: Validate answers with unit formatting (e.g. user enters 3.0 acres)
    is_valid, user_land_acres, _ = validate_answer(Field_.LAND_HECTARES, "3.0")
    _, user_income, _ = validate_answer(Field_.ANNUAL_INCOME, "1,20,000")

    # Evaluate with unit conversion (3 acres = ~1.21 hectares, which is <= 2.0 hectares -> PASS!)
    profile = UserProfile(answers={
        Field_.LAND_HECTARES: user_land_acres,
        Field_.ANNUAL_INCOME: user_income,
    })
    user_units = {Field_.LAND_HECTARES: "acres"}

    verdict = evaluate(scheme, profile, user_units=user_units)
    print("\nDeterministic Rule Evaluation:")
    print(f"  Status: {verdict.status.value}")
    print(f"  Summary: {verdict.summary}")
    for r in verdict.reasons:
        print(f"  -> {r.explanation}")
    print()


async def test_segmented_voice():
    print("=" * 65)
    print("4. MULTI-SEGMENT PARALLEL VOICE SYNTHESIS")
    print("=" * 65)

    explainer = Explainer(
        language="hi",
        segments=[
            Segment(
                text="बधाई हो! आप प्रधानमंत्री किसान सम्मान निधि योजना के लिए पूरी तरह पात्र हैं।",
                clause_ids=["c1"],
            ),
            Segment(
                text="आपको प्रति वर्ष ₹6,000 की वित्तीय सहायता सीधे बैंक खाते में प्रदान की जाएगी।",
                clause_ids=["c2"],
            ),
            Segment(
                text="आवेदन के लिए अपना आधार कार्ड और खतौनी लेकर नजदीकी सीएससी केंद्र जाएं।",
                clause_ids=["c3"],
            ),
        ],
        checklist=["आधार कार्ड", "ज़मीन की खतौनी (भूलेख)", "बैंक पासबुक"],
    )

    tts = EdgeTTSProvider()
    print("Synthesizing 3 voice segments in parallel...")
    updated_explainer = await synthesize_explainer_voice(explainer, doc_id="demo_kisan", tts=tts)

    print(f"Generated {len(updated_explainer.audio_urls)} audio segment files:")
    for idx, seg in enumerate(updated_explainer.segments, 1):
        print(f"  Segment {idx} [{seg.clause_ids[0]}]: {seg.audio_url}")
        print(f"    Text: \"{seg.text[:55]}...\"")

    print("\nAction Checklist:")
    for item in updated_explainer.checklist:
        print(f"  ✓ {item}")
    print()


async def test_langgraph_pipeline():
    print("=" * 65)
    print("5. LANGGRAPH STATE MACHINE (PAUSE & RESUME)")
    print("=" * 65)
    from langgraph.types import Command
    from app.graph import build_graph
    from app.schemas import VerdictStatus

    graph = build_graph()
    sample_text = (
        "1. Scheme Name: PM Kisan Samman Nidhi.\n"
        "2. Eligibility: Farmers having cultivable land up to 2 hectares are eligible.\n"
        "3. Financial Benefit: Rs. 6000 per year."
    )
    run_id = "demo_graph_run"
    config = {"configurable": {"thread_id": run_id}}

    initial_state = {
        "run_id": run_id,
        "file_bytes": sample_text.encode("utf-8"),
        "filename": "pmkisan.txt",
        "content_type": "text/plain",
        "persona": "citizen",
        "language": "hi",
        "status": "started",
        "trace": [],
        "verify_retries": 0,
    }

    print("Step 1: Starting graph execution...")
    async for event in graph.astream(initial_state, config=config):
        for node_name, output in event.items():
            if node_name != "__interrupt__":
                print(f"  [Node Completed] -> {node_name} (status: {output.get('status', 'ok')})")

    # Inspect paused state
    snap = graph.get_state(config)
    print(f"\nStep 2: Graph paused! Next node: {list(snap.next)}")
    questions = snap.values.get("questions", [])
    print(f"  Interview required ({len(questions)} question(s)):")
    for q in questions:
        print(f"    - {q.question_text} [{q.field.value}]")

    # Resume graph with answers
    print("\nStep 3: Submitting answers to resume graph (land_hectares = 1.5)...")
    resume_payload = {
        "answers": {"land_hectares": 1.5},
        "units": {"land_hectares": "hectares"},
    }
    async for event in graph.astream(Command(resume=resume_payload), config=config):
        for node_name, output in event.items():
            print(f"  [Resumed Node] -> {node_name} (status: {output.get('status', 'ok')})")

    final_snap = graph.get_state(config)
    verdict = final_snap.values.get("verdict")
    print(f"\nStep 4: Final Verdict -> {verdict.status.value}")
    print(f"  Summary: {verdict.summary}")
    print()


async def main():
    test_clause_splitting_and_bm25()
    await test_verifier()
    test_interview_and_evaluation()
    await test_segmented_voice()
    await test_langgraph_pipeline()
    print("=" * 65)
    print("ALL 5 INTERACTIVE CHECKS COMPLETED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())

