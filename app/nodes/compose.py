"""Explainer Composition Node.

Composes persona-tailored plain-language voice explainers and action checklists
with sentence-level clause citations in the requested regional language.
"""

import json
import logging
from pathlib import Path
from app.exceptions import ProviderError
from app.nodes.localize import get_language_name, get_legal_glossary
from app.providers.base import LLM
from app.schemas import AudienceType, Explainer, Scheme, Verdict

logger = logging.getLogger(__name__)


def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename
    return prompt_path.read_text(encoding="utf-8").strip()


async def compose_explainer(
    scheme: Scheme,
    verdict: Verdict,
    persona: AudienceType = AudienceType.CITIZEN,
    language: str = "hi",
    llm: LLM | None = None,
) -> Explainer:
    """Compose a localized, clause-tagged voice explainer and action checklist.

    Raises:
        ProviderError: If LLM generation fails or input LLM is None.
    """
    if llm is None:
        raise ProviderError("LLM provider instance is required for explainer composition.")

    lang_code = language.lower().strip()
    lang_name = get_language_name(lang_code)
    glossary = get_legal_glossary(lang_code)

    compose_template = _load_prompt("compose.md")
    system_instruction = compose_template.replace(
        "{target_language_name}", lang_name
    ).replace(
        "{language_code}", lang_code
    )

    # Format structured context
    user_context = {
        "persona": persona.value,
        "target_language": lang_name,
        "scheme": {
            "title": scheme.title,
            "audience": scheme.audience.value,
            "benefits": [b.model_dump() for b in scheme.benefits],
            "conditions": [c.model_dump() for c in scheme.conditions],
            "obligations": [o.model_dump() for o in scheme.obligations],
            "uncertain": scheme.uncertain,
        },
        "verdict": {
            "status": verdict.status.value,
            "summary": verdict.summary,
            "reasons": [
                {
                    "condition_field": r.condition.field.value,
                    "passed": r.passed,
                    "clause_id": r.condition.clause_id,
                    "explanation": r.explanation,
                }
                for r in verdict.reasons
            ],
            "missing_fields": [f.value for f in verdict.missing_fields],
        },
        "legal_terms_glossary_to_use": glossary,
    }

    user_prompt = (
        f"Generate the localized voice explainer and checklist for the following verified data:\n\n"
        f"{json.dumps(user_context, indent=2, ensure_ascii=False)}"
    )

    try:
        explainer = await llm.generate_structured(
            prompt=user_prompt,
            schema=Explainer,
            system_instruction=system_instruction,
            tier="strong",
        )
        explainer.language = lang_code
        return explainer
    except Exception as e:
        logger.error("Failed to compose explainer: %s", str(e))
        raise ProviderError(f"Explainer composition failed: {str(e)}") from e

