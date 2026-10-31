"""CivicFlow Pipeline Nodes.

Nodes represent discrete stages of the state graph.
Rule: Nodes call provider interfaces, never raw external SDKs.
"""

from app.nodes.ingest import IngestResult, ingest_document
from app.nodes.parse import PageText, parse_document
from app.nodes.index import BM25ClauseIndex, split_into_clauses
from app.nodes.extract import extract_scheme, group_clauses
from app.nodes.verify import verify_scheme, check_quote_substring, check_value_in_quote, parse_indian_numbers
from app.nodes.interview import generate_interview_questions, validate_answer
from app.nodes.evaluate import evaluate, normalize_units, evaluate_single_condition
from app.nodes.localize import get_language_name, get_legal_glossary
from app.nodes.compose import compose_explainer
from app.nodes.voice import synthesize_explainer_voice

__all__ = [
    "IngestResult",
    "ingest_document",
    "PageText",
    "parse_document",
    "BM25ClauseIndex",
    "split_into_clauses",
    "extract_scheme",
    "group_clauses",
    "verify_scheme",
    "check_quote_substring",
    "check_value_in_quote",
    "parse_indian_numbers",
    "generate_interview_questions",
    "validate_answer",
    "evaluate",
    "normalize_units",
    "evaluate_single_condition",
    "get_language_name",
    "get_legal_glossary",
    "compose_explainer",
    "synthesize_explainer_voice",
]

