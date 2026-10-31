"""CivicFlow Pipeline Nodes.

Nodes represent discrete stages of the state graph.
Rule: Nodes call provider interfaces, never raw external SDKs.
"""

from app.nodes.ingest import IngestResult, ingest_document
from app.nodes.parse import PageText, parse_document
from app.nodes.index import BM25ClauseIndex, split_into_clauses
from app.nodes.extract import extract_scheme, group_clauses
from app.nodes.verify import verify_scheme, check_quote_substring, check_value_in_quote, parse_indian_numbers

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
]

