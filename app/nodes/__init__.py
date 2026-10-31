"""CivicFlow Pipeline Nodes.

Nodes represent discrete stages of the state graph.
Rule: Nodes call provider interfaces, never raw external SDKs.
"""

from app.nodes.ingest import IngestResult, ingest_document
from app.nodes.parse import PageText, parse_document
from app.nodes.index import BM25ClauseIndex, split_into_clauses

__all__ = [
    "IngestResult",
    "ingest_document",
    "PageText",
    "parse_document",
    "BM25ClauseIndex",
    "split_into_clauses",
]

