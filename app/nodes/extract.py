"""Extraction Node for Structured Policy Rules.

Concurrently extracts benefits, conditions, and obligations from clause sections,
strictly enforcing the controlled vocabulary, and links all claims to verified source clauses.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.exceptions import NotAPolicy, ProviderError
from app.nodes.verify import verify_scheme
from app.providers.base import LLM
from app.schemas import (
    AudienceType,
    Benefit,
    Clause,
    Condition,
    Field_,
    Obligation,
    Operator,
    Scheme,
    SectionExtraction,
)

logger = logging.getLogger(__name__)

# Live progress tracker accessible by API status poller and SSE streams
EXTRACTION_PROGRESS: dict[str, dict[str, Any]] = {}


def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename
    return prompt_path.read_text(encoding="utf-8").strip()


def group_clauses(clauses: List[Clause], max_chars: int = 15000) -> List[List[Clause]]:
    """Group clauses into cohesive sections of manageable size for fast, accurate extraction.

    Uses balanced context chunks (~15,000 chars / ~3,500 tokens) to minimize
    round-trips while allowing Gemini to evaluate full contextual cross-references.
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


ADMIN_TERMS = {
    "state/ut", "sponsoring bank", "pfms", "it system", "department",
    "displayed at", "panchayat must", "transparency", "inter-departmental",
    "destination bank", "nodal officer", "procedure", "fund transfer",
    "shall designate", "shall prepare", "shall authorize", "database of",
    "village authority namely", "agriculture census",
}


def canonical_document_name(doc_str: str) -> Optional[str]:
    """Clean and normalize citizen/business documents, discarding government workflows."""
    if not doc_str or len(doc_str.strip()) == 0:
        return None
    clean = doc_str.strip()
    d_lower = clean.lower()

    if any(term in d_lower for term in ADMIN_TERMS):
        return None
    if len(clean) > 80:
        return None

    if "aadhaar" in d_lower:
        return "Aadhaar Card"
    if any(w in d_lower for w in ["khatauni", "land", "patta", "vanshavali", "village authority", "lineage"]):
        return "Land Ownership Record (Khatauni / Land Certificate)"
    if any(w in d_lower for w in ["passbook", "bank account", "bank statement", "bank details"]):
        return "Bank Account Passbook / Statement"
    if "self-declaration" in d_lower or "self declaration" in d_lower:
        return "Self-Declaration Form"
    if "udyam" in d_lower:
        return "Udyam Registration Certificate"
    if "pan" in d_lower:
        return "PAN Card"
    if "gst" in d_lower:
        return "GSTIN Registration"
    if "voter" in d_lower:
        return "Voter ID Card"
    if "driving" in d_lower:
        return "Driving Licence"
    if "income" in d_lower:
        return "Income Certificate"
    if "caste" in d_lower:
        return "Caste Certificate"

    return clean


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

    # 1. Group all clauses into safe balanced sections
    sections = group_clauses(clauses, max_chars=15000)
    total_sections = len(sections)
    section_results: List[SectionExtraction] = []

    pacing_sleep_sec = 2 if total_sections > 1 else 0

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
            "Extracting section %d/%d (%d clauses, ~%d chars)",
            idx + 1,
            total_sections,
            len(sec),
            sum(len(c.text) for c in sec),
        )

        res = await extract_from_section(sec, doc_id, llm)
        section_results.append(res)

        if idx < total_sections - 1 and pacing_sleep_sec > 0:
            for remaining in range(pacing_sleep_sec, 0, -1):
                rem_total = (total_sections - idx - 1) * (pacing_sleep_sec + 2) + remaining
                frac_done = (idx + (pacing_sleep_sec - remaining) / pacing_sleep_sec) / total_sections
                countdown_data = {
                    "current_section": idx + 1,
                    "total_sections": total_sections,
                    "percent": min(98, int(frac_done * 100)),
                    "estimated_seconds_remaining": rem_total,
                    "stage": f"Brief API pacing... Section {idx + 1}/{total_sections} extracted",
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

    # 2. Merge and robustly deduplicate
    title = "Government Policy Document"
    audience = AudienceType.CITIZEN
    all_benefits: List[Benefit] = []
    all_conditions: List[Condition] = []
    all_obligations: List[Obligation] = []
    all_uncertain: List[str] = []

    seen_conditions = set()
    seen_benefit_amounts = set()
    seen_benefit_descs = set()
    seen_obligations = set()

    for sec in section_results:
        if sec.title and title == "Government Policy Document":
            title = sec.title
        if sec.audience:
            audience = sec.audience

        # Process and filter conditions
        for cond in sec.conditions:
            # Filter 1: Zero land hectares is an extraction artifact from land transfer clauses
            if cond.field == Field_.LAND_HECTARES and cond.value in (0, 0.0, "0", "0.0"):
                continue

            # Filter 2: Ignore state conditions when states are mentioned only as regional administrative exceptions
            if cond.field == Field_.STATE:
                val_str = str(cond.value).lower().strip()
                if any(st in val_str for st in ["nagaland", "manipur", "assam", "meghalaya", "j&k", "jammu", "nri"]):
                    continue

            # Filter 3: Normalize boolean is_farmer
            if cond.field == Field_.IS_FARMER:
                if cond.value in (1, "1", "true", "True", True):
                    cond.value = True
                elif cond.value in (0, "0", "false", "False", False):
                    # Negative condition like "was not land owner" should not be is_farmer = False
                    continue
                else:
                    cond.value = True

            # Filter 4: Inverted exclusions (e.g. category in Institutional landholders)
            if cond.field == Field_.CATEGORY and "institutional" in str(cond.value).lower():
                cond.field = Field_.BUSINESS_TYPE
                cond.operator = Operator.NEQ
                cond.value = "Institutional Landholder"

            # Clean key WITHOUT clause_id prevents same rule on different pages from duplicating
            cond_key = (cond.field, cond.operator, str(cond.value).strip().lower())
            if cond_key not in seen_conditions:
                seen_conditions.add(cond_key)
                all_conditions.append(cond)

        # Process and deduplicate benefits
        for ben in sec.benefits:
            amt_key = (ben.amount, (ben.frequency or "").strip().lower()) if ben.amount else None
            desc_norm = ben.description.strip().lower()

            # Skip duplicate monetary amounts or duplicate descriptions
            if amt_key and amt_key in seen_benefit_amounts:
                continue
            if desc_norm in seen_benefit_descs:
                continue

            # Check for significant duplicate phrases across DBT / cash grants
            is_duplicate = False
            for prev_desc in seen_benefit_descs:
                if ("6000" in desc_norm and "6000" in prev_desc) or ("dbt" in desc_norm and "dbt" in prev_desc):
                    is_duplicate = True
                    break
            if is_duplicate:
                continue

            if amt_key:
                seen_benefit_amounts.add(amt_key)
            seen_benefit_descs.add(desc_norm)
            all_benefits.append(ben)

        # Process and filter obligations
        for ob in sec.obligations:
            # Clean and canonicalize required_documents
            clean_docs: list[str] = []
            seen_doc_names = set()
            for doc in (ob.required_documents or []):
                canon = canonical_document_name(doc)
                if canon and canon.lower() not in seen_doc_names:
                    seen_doc_names.add(canon.lower())
                    clean_docs.append(canon)
            ob.required_documents = clean_docs

            # Deduplicate obligations by description prefix without clause_id
            ob_key = (ob.description.strip().lower()[:50], ob.deadline)
            if ob_key not in seen_obligations:
                seen_obligations.add(ob_key)
                all_obligations.append(ob)

        all_uncertain.extend(sec.uncertain)

    # Domain policy validation: ensure uploaded document is a genuine policy/scheme
    is_explicit_non_policy = any(
        "not_a_government_policy" in u.lower() or "not a government policy" in u.lower() or "not a policy" in u.lower()
        for u in all_uncertain
    )
    if is_explicit_non_policy:
        raise NotAPolicy(
            "The uploaded document does not appear to be an official government policy, welfare scheme, or legal act. CivicFlow only processes government welfare schemes, policies, and municipal regulations."
        )

    if clauses and len(all_conditions) == 0 and len(all_benefits) == 0 and len(all_obligations) == 0:
        sample_text = " ".join(c.text for c in clauses[:5]).lower()
        civic_keywords = [
            "scheme", "policy", "guideline", "guidelines", "government", "ministry",
            "department", "yojana", "act", "gazette", "beneficiary", "beneficiaries",
            "eligibility", "grant", "subsidy", "assistance", "notification", "shasan",
            "kisan", "pradhan", "mantri", "panchayat", "municipal", "rules", "welfare"
        ]
        if not any(kw in sample_text for kw in civic_keywords):
            raise NotAPolicy(
                "The uploaded document does not contain any government welfare scheme, policy rules, or citizen rights. Please upload an official government policy or scheme document."
            )

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
