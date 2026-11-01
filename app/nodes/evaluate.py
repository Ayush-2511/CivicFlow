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

FIELD_HUMAN_NAMES: Dict[str, str] = {
    "annual_turnover": "annual business turnover",
    "annual_income": "annual household income",
    "business_type": "enterprise classification",
    "land_hectares": "agricultural landholding",
    "occupation": "primary occupation",
    "state": "state of residence",
    "category": "social/economic category",
    "gender": "gender",
    "age": "age",
    "is_farmer": "agricultural engagement",
    "is_student": "student enrollment",
    "has_disability": "certified disability",
    "employees": "number of full-time employees",
}


def _friendly_field(field_val: str) -> str:
    """Return plain-language human name for a field identifier."""
    return FIELD_HUMAN_NAMES.get(field_val, field_val.replace("_", " "))


def _format_currency_inr(val: float) -> str:
    """Format numeric values as Indian Currency (Crore, Lakh, or INR)."""
    abs_val = abs(val)
    if abs_val >= 10_000_000:
        cr = val / 10_000_000
        formatted_cr = f"{cr:g}"
        return f"₹{formatted_cr} Crore (₹{int(val):,} INR)"
    elif abs_val >= 100_000:
        lk = val / 100_000
        formatted_lk = f"{lk:g}"
        return f"₹{formatted_lk} Lakh (₹{int(val):,} INR)"
    else:
        return f"₹{int(val):,} INR"


def _format_value_with_unit(val: float, unit: Optional[str]) -> str:
    """Format numeric values cleanly with units without raw float artifacts."""
    if unit:
        u_clean = unit.lower().strip()
        if u_clean in ["inr", "rupees", "rs"]:
            return _format_currency_inr(val)
        if u_clean in ["hectare", "hectares", "ha"]:
            return f"{val:g} hectares"
        if u_clean in ["acre", "acres"]:
            return f"{val:g} acres"
        if u_clean in ["years", "year"]:
            return f"{int(val)} years"
        return f"{val:g} {unit}"
    return f"{val:g}"


def _format_human_list(items: Any) -> str:
    """Format list of values into a natural English sequence."""
    if not isinstance(items, list):
        return f"'{items}'"
    clean_items = [f"'{x}'" for x in items if x is not None]
    if not clean_items:
        return "none"
    if len(clean_items) == 1:
        return clean_items[0]
    if len(clean_items) == 2:
        return f"{clean_items[0]} or {clean_items[1]}"
    return ", ".join(clean_items[:-1]) + f", or {clean_items[-1]}"


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
    """Evaluate a single condition against the user profile using clear natural language sentences."""
    field_title = _friendly_field(condition.field.value)

    if condition.field not in user_profile:
        return Reason(
            condition=condition,
            passed=None,
            explanation=f"Awaiting your details for {field_title} to evaluate eligibility.",
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
        user_str = _format_value_with_unit(user_val, condition.unit)
        c_str = _format_value_with_unit(c_val, condition.unit)

        if operator_key == "lte":
            if passed:
                explanation = (
                    f"Your {field_title} is {user_str}, which satisfies the requirement "
                    f"of not exceeding {c_str}."
                )
            else:
                explanation = (
                    f"Your {field_title} is {user_str}, which exceeds the maximum allowed "
                    f"limit of {c_str}."
                )
        elif operator_key == "lt":
            if passed:
                explanation = (
                    f"Your {field_title} is {user_str}, which satisfies the limit "
                    f"of less than {c_str}."
                )
            else:
                explanation = (
                    f"Your {field_title} is {user_str}, which must be strictly below {c_str}."
                )
        elif operator_key == "gte":
            if passed:
                explanation = (
                    f"Your {field_title} is {user_str}, meeting the minimum threshold "
                    f"of {c_str}."
                )
            else:
                explanation = (
                    f"Your {field_title} is {user_str}, which is below the minimum required "
                    f"threshold of {c_str}."
                )
        elif operator_key == "gt":
            if passed:
                explanation = (
                    f"Your {field_title} is {user_str}, exceeding the required baseline "
                    f"of {c_str}."
                )
            else:
                explanation = (
                    f"Your {field_title} is {user_str}, which must be greater than {c_str}."
                )
        elif operator_key == "eq":
            if passed:
                explanation = (
                    f"Your {field_title} is {user_str}, matching the required value of {c_str}."
                )
            else:
                explanation = (
                    f"Your {field_title} is {user_str}, but the scheme requires {c_str}."
                )
        elif operator_key == "neq":
            if passed:
                explanation = (
                    f"Your {field_title} is {user_str}, which is not {c_str} as required."
                )
            else:
                explanation = (
                    f"Your {field_title} is {user_str}, which is not permitted under this scheme."
                )
        else:
            explanation = (
                f"Your {field_title} is {user_str}, which {'meets' if passed else 'does not meet'} "
                f"the required criteria of {c_str}."
            )

        return Reason(condition=condition, passed=passed, explanation=explanation)

    # Boolean evaluation
    if isinstance(raw_user_value, bool) or isinstance(cond_value, bool):
        passed = bool(raw_user_value) == bool(cond_value)
        if operator_key == "neq":
            passed = not passed

        if passed:
            explanation = (
                f"Your status for {field_title} fulfills the mandatory criteria specified in the circular."
            )
        else:
            explanation = (
                f"Your status for {field_title} does not fulfill the mandatory eligibility requirement."
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

        if operator_key == "in":
            allowed_str = _format_human_list(cond_value)
            if passed:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', which is recognized as an eligible "
                    f"category ({allowed_str})."
                )
            else:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', but this scheme is exclusively "
                    f"reserved for {allowed_str}."
                )
        elif operator_key == "not_in":
            excluded_str = _format_human_list(cond_value)
            if passed:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', which is eligible and not among "
                    f"the excluded categories ({excluded_str})."
                )
            else:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', which falls under the excluded "
                    f"categories ({excluded_str})."
                )
        elif operator_key == "eq":
            if passed:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', which satisfies the required "
                    f"specification of '{cond_value}'."
                )
            else:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', whereas the scheme requires '{cond_value}'."
                )
        elif operator_key == "neq":
            if passed:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', correctly excluding '{cond_value}'."
                )
            else:
                explanation = (
                    f"Your {field_title} is '{raw_user_value}', which is an excluded category."
                )
        else:
            explanation = (
                f"Your {field_title} is '{raw_user_value}', which {'meets' if passed else 'does not meet'} "
                f"the policy condition."
            )

        return Reason(condition=condition, passed=passed, explanation=explanation)

    # Fallback comparison
    passed = op_func(raw_user_value, cond_value)
    explanation = (
        f"Your {field_title} {'meets' if passed else 'does not meet'} "
        f"the policy criteria."
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
        deciding_clauses = list({r.condition.clause_id for r in failed_reasons if r.condition and r.condition.clause_id})
        clause_str = f" in clause(s): {', '.join(deciding_clauses)}" if deciding_clauses else ""
        summary = (
            f"Not Eligible. Disqualified based on {len(failed_reasons)} condition(s){clause_str}."
        )
    elif missing_fields:
        status = VerdictStatus.MAYBE
        field_names = [_friendly_field(f.value) for f in missing_fields]
        summary = (
            f"Eligibility Pending. Requires answers for {len(missing_fields)} missing detail(s): "
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
