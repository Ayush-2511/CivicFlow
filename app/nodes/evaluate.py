"""Deterministic Eligibility Rule Engine.

Pure Python implementation: zero LLM calls, zero hallucinations.
Evaluates structured conditions against validated user profiles,
handles unit conversions, and outputs YES/NO/MAYBE verdicts citing exact clauses.
"""

from typing import Any, Callable, Dict, List, Optional
from app.schemas import (
    Condition,
    Field_,
    Operator,
    Reason,
    Scheme,
    UserProfile,
    Verdict,
    VerdictStatus,
)

# Comparison operator dispatcher
OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "in": lambda a, b: (
        a.lower() in [str(x).lower() for x in b]
        if isinstance(a, str) and isinstance(b, list)
        else a in b
    ),
    "not_in": lambda a, b: (
        a.lower() not in [str(x).lower() for x in b]
        if isinstance(a, str) and isinstance(b, list)
        else a not in b
    ),
}

OPERATOR_SYMBOLS: Dict[str, str] = {
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "eq": "==",
    "neq": "!=",
    "in": "in",
    "not_in": "not in",
}


def normalize_units(
    value: float,
    from_unit: Optional[str],
    to_unit: Optional[str],
) -> float:
    """Normalize numeric units between user input and condition criteria.

    Supports:
    - Land: acres <-> hectares (1 hectare = 2.47105 acres)
    - Indian Currency: lakh -> INR (10^5), crore -> INR (10^7)
    """
    if not from_unit or not to_unit or from_unit.lower() == to_unit.lower():
        return value

    f_unit = from_unit.lower().strip()
    t_unit = to_unit.lower().strip()

    # Land conversions
    if f_unit in ["acre", "acres"] and t_unit in ["hectare", "hectares", "ha"]:
        return round(value * 0.404686, 4)
    if f_unit in ["hectare", "hectares", "ha"] and t_unit in ["acre", "acres"]:
        return round(value * 2.47105, 4)

    # Indian Currency conversions
    if f_unit in ["lakh", "lakhs", "l"] and t_unit in ["inr", "rupees", "rs"]:
        return value * 100_000.0
    if f_unit in ["crore", "crores", "cr"] and t_unit in ["inr", "rupees", "rs"]:
        return value * 10_000_000.0
    if f_unit in ["inr", "rupees", "rs"] and t_unit in ["lakh", "lakhs", "l"]:
        return value / 100_000.0

    return value


def evaluate_single_condition(
    condition: Condition,
    user_profile: UserProfile,
    user_units: Optional[Dict[Field_, str]] = None,
) -> Reason:
    """Evaluate a single condition against the user profile."""
    if condition.field not in user_profile:
        return Reason(
            condition=condition,
            passed=None,
            explanation=f"Missing answer for '{condition.field.value}' (Cited in {condition.clause_id})",
        )

    raw_user_value = user_profile.get(condition.field)
    cond_value = condition.value
    operator_key = condition.operator.value
    op_func = OPS.get(operator_key)

    if op_func is None:
        raise ValueError(f"Unsupported operator: {operator_key}")

    # Numeric evaluation with potential unit conversion
    if isinstance(raw_user_value, (int, float)) and isinstance(cond_value, (int, float)):
        user_val = float(raw_user_value)
        c_val = float(cond_value)

        # Normalize units if specified
        if user_units and condition.field in user_units:
            user_unit = user_units[condition.field]
            user_val = normalize_units(user_val, from_unit=user_unit, to_unit=condition.unit)

        passed = op_func(user_val, c_val)
        symbol = OPERATOR_SYMBOLS.get(operator_key, operator_key)
        status_label = "PASSED" if passed else "FAILED"
        unit_str = f" {condition.unit}" if condition.unit else ""

        explanation = (
            f"Your {condition.field.value} of {user_val}{unit_str} {symbol} "
            f"condition of {c_val}{unit_str} -> {status_label} (Clause {condition.clause_id})"
        )
        return Reason(condition=condition, passed=passed, explanation=explanation)

    # Boolean evaluation
    if isinstance(raw_user_value, bool) or isinstance(cond_value, bool):
        passed = bool(raw_user_value) == bool(cond_value)
        if operator_key == "neq":
            passed = not passed
        status_label = "PASSED" if passed else "FAILED"
        explanation = (
            f"Your {condition.field.value} is {raw_user_value} -> {status_label} "
            f"(Clause {condition.clause_id})"
        )
        return Reason(condition=condition, passed=passed, explanation=explanation)

    # String / Categorical evaluation (case-insensitive)
    if isinstance(raw_user_value, str):
        if isinstance(cond_value, str):
            passed = op_func(raw_user_value.strip().lower(), cond_value.strip().lower())
        elif isinstance(cond_value, list):
            passed = op_func(raw_user_value.strip(), cond_value)
        else:
            passed = op_func(raw_user_value, cond_value)

        symbol = OPERATOR_SYMBOLS.get(operator_key, operator_key)
        status_label = "PASSED" if passed else "FAILED"
        explanation = (
            f"Your {condition.field.value} ('{raw_user_value}') {symbol} "
            f"'{cond_value}' -> {status_label} (Clause {condition.clause_id})"
        )
        return Reason(condition=condition, passed=passed, explanation=explanation)

    # Fallback comparison
    passed = op_func(raw_user_value, cond_value)
    status_label = "PASSED" if passed else "FAILED"
    explanation = (
        f"Evaluation of {condition.field.value} -> {status_label} (Clause {condition.clause_id})"
    )
    return Reason(condition=condition, passed=passed, explanation=explanation)


def evaluate(
    scheme: Scheme,
    user_profile: UserProfile,
    user_units: Optional[Dict[Field_, str]] = None,
) -> Verdict:
    """Evaluate all scheme conditions against the user profile deterministically.

    Status resolution:
    - If ANY condition fails -> 'NO'
    - If any condition has missing answers -> 'MAYBE'
    - If all pass, but scheme contains uncertain clauses -> 'MAYBE' (subject to verification)
    - If all pass and no uncertainties -> 'YES'
    """
    reasons: List[Reason] = []
    missing_fields: List[Field_] = []

    for cond in scheme.conditions:
        reason = evaluate_single_condition(cond, user_profile, user_units=user_units)
        reasons.append(reason)
        if reason.passed is None and cond.field not in missing_fields:
            missing_fields.append(cond.field)

    failed_reasons = [r for r in reasons if r.passed is False]

    if failed_reasons:
        status = VerdictStatus.NO
        deciding_clauses = list({r.condition.clause_id for r in failed_reasons})
        summary = (
            f"Not Eligible. Disqualified by {len(failed_reasons)} condition(s) "
            f"in clause(s): {', '.join(deciding_clauses)}."
        )
    elif missing_fields:
        status = VerdictStatus.MAYBE
        field_names = [f.value for f in missing_fields]
        summary = (
            f"Eligibility Pending. Requires answers for {len(missing_fields)} missing field(s): "
            f"{', '.join(field_names)}."
        )
    elif scheme.uncertain:
        status = VerdictStatus.MAYBE
        summary = (
            f"Eligible based on evaluated criteria, subject to manual review of "
            f"{len(scheme.uncertain)} ambiguous/unverified clause(s)."
        )
    else:
        status = VerdictStatus.YES
        summary = (
            f"Eligible! Satisfied all {len(scheme.conditions)} criteria from official clauses."
        )

    return Verdict(
        status=status,
        reasons=reasons,
        missing_fields=missing_fields,
        summary=summary,
    )

