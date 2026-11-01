"""Extraction Node for Structured Policy Rules.

Concurrently extracts benefits, conditions, and obligations from clause sections,
strictly enforcing the controlled vocabulary, and links all claims to verified source clauses.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.exceptions import ProviderError
from app.nodes.verify import verify_scheme
from app.providers.base import LLM
from app.schemas import (
    AudienceType,
    Benefit,
    Clause,
    Condition,
    Obligation,
    Scheme,
    SectionExtraction,
)

logger = logging.getLogger(__name__)

# Live progress tracker accessible by API status poller and SSE streams
EXTRACTION_PROGRESS: dict[str, dict[str, Any]] = {}


def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename
    return prompt_path.read_text(encoding="utf-8").strip()


def group_clauses(clauses: List[Clause], max_chars: int = 6000) -> List[List[Clause]]:
    """Group clauses into cohesive sections of manageable size for rate-safe extraction.

    Uses balanced context-aware chunks (~6,000 chars / ~1,400 tokens) to minimize
    token rate-limit impact while keeping LLM reasoning sharp and structured.
    """
    groups: List[List[Clause]] = []
    current_group: List[Clause] = []
    current_chars = 0

    for clause in clauses:
        clause_len = len(clause.text)
        if current_chars + clause_len > max_chars and current_group:
            groups.append(current_group)
            current_group = [clause]
            current_chars = clause_len
        else:
            current_group.append(clause)
            current_chars += clause_len

    if current_group:
        groups.append(current_group)

    return groups


async def extract_from_section(
    section_clauses: List[Clause],
    doc_id: str,
    llm: LLM,
) -> SectionExtraction:
    """Extract structured rules from a group of clauses using the LLM."""
    extract_prompt = _load_prompt("extract.md")

    # Format clauses clearly with IDs and page numbers
    clause_blocks = []
    for c in section_clauses:
        clause_blocks.append(f"[CLAUSE_ID: {c.id}] (Page {c.page}):\n{c.text}\n")
    user_prompt = "OFFICIAL DOCUMENT CLAUSES:\n\n" + "\n---\n".join(clause_blocks)

    try:
        extraction = await llm.generate_structured(
            prompt=user_prompt,
            schema=SectionExtraction,
            system_instruction=extract_prompt,
            tier="fast",
        )
        return extraction
    except Exception as e:
        logger.error("Section extraction failed: %s", str(e))
        # Return fallback empty extraction with error noted in uncertain
        return SectionExtraction(
            uncertain=[f"Extraction failed for section containing clauses {section_clauses[0].id}...: {str(e)}"]
        )


async def extract_scheme(
    clauses: List[Clause],
    doc_id: str,
    llm: LLM,
    verify: bool = True,
    run_id: Optional[str] = None,
) -> Scheme:
    """Extract, merge, deduplicate, and verify a complete Scheme model from clauses."""
    if not clauses:
        return Scheme(doc_id=doc_id, title="Empty Document", confidence=0.0)

    # 1. Group all clauses into safe balanced sections (~6,000 chars / ~1,400 tokens)
    # Processing all clauses ensures 100% eligibility rules, exclusions, and benefits are extracted
    sections = group_clauses(clauses, max_chars=6000)
    total_sections = len(sections)
    section_results: List[SectionExtraction] = []

    # Pace calls evenly over ~1.5 - 2 minutes to stay strictly under the 8,000 TPM limit
    pacing_sleep_sec = 18 if total_sections > 1 else 0

    for idx, sec in enumerate(sections):
        est_remaining = max(0, (total_sections - idx) * (pacing_sleep_sec + 2))
        progress_data = {
            "current_section": idx + 1,
            "total_sections": total_sections,
            "percent": int((idx / total_sections) * 100),
            "estimated_seconds_remaining": est_remaining,
            "stage": f"Analyzing clauses {sec[0].id} to {sec[-1].id} (Section {idx + 1} of {total_sections})",
        }
        EXTRACTION_PROGRESS[doc_id] = progress_data
        if run_id:
            EXTRACTION_PROGRESS[run_id] = progress_data

        logger.info(
            "Extracting section %d/%d (%d clauses, ~%d chars) with rate-limit pacing",
            idx + 1,
            total_sections,
            len(sec),
            sum(len(c.text) for c in sec),
        )

        res = await extract_from_section(sec, doc_id, llm)
        section_results.append(res)

        # Countdown live timer between sections
        if idx < total_sections - 1:
            for remaining in range(pacing_sleep_sec, 0, -1):
                rem_total = (total_sections - idx - 1) * (pacing_sleep_sec + 2) + remaining
                frac_done = (idx + (pacing_sleep_sec - remaining) / pacing_sleep_sec) / total_sections
                countdown_data = {
                    "current_section": idx + 1,
                    "total_sections": total_sections,
                    "percent": min(98, int(frac_done * 100)),
                    "estimated_seconds_remaining": rem_total,
                    "stage": f"Pacing API token rate limit... Section {idx + 1}/{total_sections} extracted",
                }
                EXTRACTION_PROGRESS[doc_id] = countdown_data
                if run_id:
                    EXTRACTION_PROGRESS[run_id] = countdown_data
                await asyncio.sleep(1.0)

    # Mark extraction complete
    complete_data = {
        "current_section": total_sections,
        "total_sections": total_sections,
        "percent": 100,
        "estimated_seconds_remaining": 0,
        "stage": "All policy sections extracted and compiled",
    }
    EXTRACTION_PROGRESS[doc_id] = complete_data
    if run_id:
        EXTRACTION_PROGRESS[run_id] = complete_data

    # 2. Merge and deduplicate
    title = "Government Policy Document"
    audience = AudienceType.CITIZEN
    all_benefits: List[Benefit] = []
    all_conditions: List[Condition] = []
    all_obligations: List[Obligation] = []
    all_uncertain: List[str] = []

    seen_conditions = set()
    seen_benefits = set()
    seen_obligations = set()

    for sec in section_results:
        if sec.title and title == "Government Policy Document":
            title = sec.title
        if sec.audience:
            audience = sec.audience

        for cond in sec.conditions:
            cond_key = (cond.field, cond.operator, str(cond.value), cond.clause_id)
            if cond_key not in seen_conditions:
                seen_conditions.add(cond_key)
                all_conditions.append(cond)

        for ben in sec.benefits:
            ben_key = (ben.description.strip().lower(), ben.amount, ben.clause_id)
            if ben_key not in seen_benefits:
                seen_benefits.add(ben_key)
                all_benefits.append(ben)

        for ob in sec.obligations:
            ob_key = (ob.description.strip().lower(), ob.deadline, ob.clause_id)
            if ob_key not in seen_obligations:
                seen_obligations.add(ob_key)
                all_obligations.append(ob)

        all_uncertain.extend(sec.uncertain)

    raw_scheme = Scheme(
        doc_id=doc_id,
        title=title,
        audience=audience,
        benefits=all_benefits,
        conditions=all_conditions,
        obligations=all_obligations,
        uncertain=all_uncertain,
        confidence=1.0,
    )

    # 3. Multi-stage verification pass
    if verify:
        return await verify_scheme(raw_scheme, clauses, llm=llm)

    return raw_scheme

