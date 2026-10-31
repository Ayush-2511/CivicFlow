"""Self-Correcting Verification Node.

Implements multi-stage verification for every extracted claim:
1. Fast normalized substring matching (zero-cost)
2. Indian number format normalization and value matching (lakh, crore, INR)
3. LLM re-check pass for edge cases
4. Ambiguous / unsupported facts are safely routed to `uncertain`
"""

import difflib
import logging
import re
from pathlib import Path
from typing import List, Optional
from app.exceptions import ProviderError
from app.providers.base import LLM
from app.schemas import Benefit, Cited, Clause, Condition, Obligation, Scheme, VerificationResult

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text for substring comparison."""
    if not text:
        return ""
    # Lowercase, replace smart quotes/dashes, collapse whitespace
    s = text.lower()
    s = re.sub(r"[\u2018\u2019\u201c\u201d]", "'", s)
    s = re.sub(r"[\u2013\u2014]", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def parse_indian_numbers(text: str) -> List[float]:
    """Extract and normalize numbers from text, including Indian currency notations.

    Supports:
    - '1.5 lakh', '1.5 Lakhs', '1.5L' -> 150,000.0
    - '2 crore', '2 Crores', '2Cr' -> 20,000,000.0
    - 'Rs. 6,000/-', '₹ 6,000', '1,50,000' -> 6000.0, 150000.0
    - standard decimals and integers: '2.0', '18', '2'
    """
    normalized = normalize_text(text)
    numbers: list[float] = []

    # 1. Match Lakh patterns: e.g. "1.5 lakh", "2 lakhs", "1.5l"
    lakh_pattern = re.finditer(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|l)\b", normalized)
    for m in lakh_pattern:
        try:
            val = float(m.group(1)) * 100_000.0
            numbers.append(val)
        except ValueError:
            pass

    # 2. Match Crore patterns: e.g. "2 crore", "5 crores", "2cr"
    crore_pattern = re.finditer(r"(\d+(?:\.\d+)?)\s*(?:crores?|cr)\b", normalized)
    for m in crore_pattern:
        try:
            val = float(m.group(1)) * 10_000_000.0
            numbers.append(val)
        except ValueError:
            pass

    # 3. Match standard numbers with optional commas: e.g. "1,50,000", "6000", "2.5"
    num_pattern = re.finditer(r"(?<![\w])(?:rs\.?|inr|₹)?\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])", normalized)
    for m in num_pattern:
        raw_num = m.group(1).replace(",", "")
        try:
            numbers.append(float(raw_num))
        except ValueError:
            pass

    return numbers


def check_quote_substring(item: Cited, clauses: dict[str, Clause]) -> bool:
    """Verify that quote is an authentic substring of the source clause."""
    clause = clauses.get(item.clause_id)
    if not clause:
        return False

    norm_quote = normalize_text(item.quote)
    norm_clause = normalize_text(clause.text)

    if not norm_quote:
        return False

    # Direct substring check
    if norm_quote in norm_clause:
        return True

    # Fuzzy tolerance for minor OCR or whitespace deviations
    if len(norm_quote) > 20:
        matcher = difflib.SequenceMatcher(None, norm_quote, norm_clause)
        match = matcher.find_longest_match(0, len(norm_quote), 0, len(norm_clause))
        if match.size / len(norm_quote) >= 0.85:
            return True

    return False


def check_value_in_quote(item: Condition | Benefit, quote_text: str) -> bool:
    """Check if the numeric value asserted in the extracted item is present in the quote."""
    target_value: Optional[float] = None

    if isinstance(item, Condition) and isinstance(item.value, (int, float)):
        target_value = float(item.value)
    elif isinstance(item, Benefit) and item.amount is not None:
        target_value = float(item.amount)

    if target_value is None:
        # String condition or non-numeric fact: trivially passes value check
        return True

    extracted_numbers = parse_indian_numbers(quote_text)
    if not extracted_numbers:
        return False

    # Check if target_value is close to any number in quote
    return any(abs(num - target_value) < 0.01 for num in extracted_numbers)


def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename
    return prompt_path.read_text(encoding="utf-8").strip()


async def verify_item_llm(
    item: Cited,
    clause: Clause,
    llm: LLM,
) -> VerificationResult:
    """LLM fallback verification for borderline or flagged claims."""
    verify_prompt = _load_prompt("verify.md")
    user_prompt = (
        f"SOURCE CLAUSE (ID: {clause.id}):\n{clause.text}\n\n"
        f"CITED QUOTE:\n{item.quote}\n\n"
        f"EXTRACTED FACT:\n{item.model_dump_json()}"
    )

    try:
        result = await llm.generate_structured(
            prompt=user_prompt,
            schema=VerificationResult,
            system_instruction=verify_prompt,
            tier="fast",
        )
        return result
    except Exception as e:
        logger.warning("LLM verification call failed: %s", str(e))
        return VerificationResult(
            is_supported=False,
            reason=f"LLM verification failed with error: {str(e)}",
        )


async def verify_scheme(
    scheme: Scheme,
    clauses: List[Clause],
    llm: LLM | None = None,
) -> Scheme:
    """Verify all conditions, benefits, and obligations in a scheme.

    Removes unsupported claims and logs them to scheme.uncertain.
    Updates confidence score based on ratio of passed items.
    """
    clause_map = {c.id: c for c in clauses}
    verified_conditions: List[Condition] = []
    verified_benefits: List[Benefit] = []
    verified_obligations: List[Obligation] = []
    uncertain_items: List[str] = list(scheme.uncertain)

    total_items = len(scheme.conditions) + len(scheme.benefits) + len(scheme.obligations)
    if total_items == 0:
        return scheme

    passed_count = 0

    # 1. Verify Conditions
    for cond in scheme.conditions:
        clause = clause_map.get(cond.clause_id)
        if not clause:
            uncertain_items.append(f"Condition cites non-existent clause '{cond.clause_id}'")
            continue

        quote_ok = check_quote_substring(cond, clause_map)
        val_ok = check_value_in_quote(cond, cond.quote) if quote_ok else False

        if quote_ok and val_ok:
            verified_conditions.append(cond)
            passed_count += 1
            continue

        # Trigger LLM re-check if available
        if llm:
            llm_result = await verify_item_llm(cond, clause, llm)
            if llm_result.is_supported:
                if llm_result.corrected_quote:
                    cond.quote = llm_result.corrected_quote
                verified_conditions.append(cond)
                passed_count += 1
                continue

        uncertain_items.append(
            f"Condition '{cond.field.value} {cond.operator.value} {cond.value}' failed quote/value verification in {cond.clause_id}"
        )

    # 2. Verify Benefits
    for ben in scheme.benefits:
        clause = clause_map.get(ben.clause_id)
        if not clause:
            uncertain_items.append(f"Benefit cites non-existent clause '{ben.clause_id}'")
            continue

        quote_ok = check_quote_substring(ben, clause_map)
        val_ok = check_value_in_quote(ben, ben.quote) if quote_ok else False

        if quote_ok and val_ok:
            verified_benefits.append(ben)
            passed_count += 1
            continue

        if llm:
            llm_result = await verify_item_llm(ben, clause, llm)
            if llm_result.is_supported:
                if llm_result.corrected_quote:
                    ben.quote = llm_result.corrected_quote
                verified_benefits.append(ben)
                passed_count += 1
                continue

        uncertain_items.append(
            f"Benefit '{ben.description}' failed quote verification in clause {ben.clause_id}"
        )

    # 3. Verify Obligations
    for ob in scheme.obligations:
        clause = clause_map.get(ob.clause_id)
        if not clause:
            uncertain_items.append(f"Obligation cites non-existent clause '{ob.clause_id}'")
            continue

        quote_ok = check_quote_substring(ob, clause_map)
        if quote_ok:
            verified_obligations.append(ob)
            passed_count += 1
            continue

        if llm:
            llm_result = await verify_item_llm(ob, clause, llm)
            if llm_result.is_supported:
                if llm_result.corrected_quote:
                    ob.quote = llm_result.corrected_quote
                verified_obligations.append(ob)
                passed_count += 1
                continue

        uncertain_items.append(
            f"Obligation '{ob.description}' failed quote verification in clause {ob.clause_id}"
        )

    confidence = round(passed_count / total_items, 2) if total_items > 0 else 1.0

    return Scheme(
        doc_id=scheme.doc_id,
        title=scheme.title,
        audience=scheme.audience,
        summary=scheme.summary,
        benefits=verified_benefits,
        conditions=verified_conditions,
        obligations=verified_obligations,
        uncertain=uncertain_items,
        confidence=confidence,
    )

