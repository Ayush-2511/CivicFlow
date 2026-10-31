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
from app.providers.speech import EdgeTTSProvider
from app.schemas import (
    AudienceType,
    Clause,
    Condition,
    Field_,
    Operator,
    Scheme,
)


def test_clause_splitting_and_bm25():
    print("=" * 60)
    print("1. TESTING CLAUSE SPLITTING & BM25 SEARCH")
    print("=" * 60)

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

    print("\n--- Testing BM25 Search for query: 'land limit 2 hectares' ---")
    index = BM25ClauseIndex(clauses)
    top_matches = index.search("land limit 2 hectares", top_k=1)
    if top_matches:
        print(f"  Top Match [{top_matches[0].id}]: {top_matches[0].text}\n")


async def test_verifier():
    print("=" * 60)
    print("2. TESTING SELF-CORRECTING VERIFIER (CATCHING A PLANTED LIE)")
    print("=" * 60)

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

    # 2. Planted lie (quote doesn't exist, value fabricated)
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
    print(f"  Overall confidence score: {verified.confidence * 100}%\n")


async def test_voice_synthesis():
    print("=" * 60)
    print("3. TESTING REGIONAL VOICE SYNTHESIS (HINDI TTS)")
    print("=" * 60)

    tts = EdgeTTSProvider()
    hindi_text = (
        "नमस्ते! प्रधानमंत्री किसान सम्मान निधि योजना के तहत "
        "2 हेक्टेयर से कम भूमि वाले किसानों को प्रति वर्ष ₹6,000 की वित्तीय सहायता दी जाएगी।"
    )
    print("Synthesizing audio for text:")
    print(f"  \"{hindi_text}\"")

    audio_bytes = await tts.synthesize(hindi_text, language="hi")
    output_filename = "test_voice.mp3"
    with open(output_filename, "wb") as f:
        f.write(audio_bytes)

    print(f"\nSuccess! Generated {len(audio_bytes)} bytes of playable MP3 audio.")
    print(f"File saved to: {output_filename} (double-click to listen!)\n")


async def main():
    test_clause_splitting_and_bm25()
    await test_verifier()
    await test_voice_synthesis()
    print("=" * 60)
    print("ALL INTERACTIVE CHECKS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
