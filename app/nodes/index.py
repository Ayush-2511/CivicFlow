"""Clause Splitting and BM25 Indexing Node.

Splits document page text into atomic numbered clauses with stable IDs,
and provides an in-memory BM25 index for fast retrieval.
"""

import re
from typing import List, Optional
from rank_bm25 import BM25Okapi
from app.schemas import Clause

# Pattern matching legal clause and section headers at the start of a line
CLAUSE_SPLIT_PATTERN = re.compile(
    r"(?=(?:^|\n)\s*(?:"
    r"(?:Section|Sec\.|Clause|Article|Rule)\s+\d+[a-zA-Z]?[.:\s]"
    r"|\d+[\.\)]\s+"
    r"|\([0-9a-zA-Z]+\)\s+"
    r"|[A-Z][\.\)]\s+"
    r"|\d+\.\d+(?:\.\d+)?\s+"
    r"))",
    re.MULTILINE | re.IGNORECASE,
)


def _tokenize(text: str) -> list[str]:
    """Tokenize query and documents for BM25 matching."""
    return re.findall(r"\b\w{2,}\b", text.lower())


def split_into_clauses(pages: list, doc_id: str) -> List[Clause]:
    """Split a list of PageText items into atomic Clause objects with stable IDs."""
    clauses: List[Clause] = []
    short_doc_id = doc_id[:6]

    for p in pages:
        page_num = p.page
        page_text = p.text.strip()
        if not page_text:
            continue

        # Try splitting by legal clause headers first
        raw_chunks = [c.strip() for c in CLAUSE_SPLIT_PATTERN.split(page_text) if c.strip()]

        # If legal split found no structure, split by paragraphs
        if len(raw_chunks) <= 1:
            raw_chunks = [c.strip() for c in re.split(r"\n\s*\n", page_text) if c.strip()]

        # Process chunks, sub-splitting any overly long chunks (> 1200 chars)
        final_chunks: list[str] = []
        for chunk in raw_chunks:
            if len(chunk) > 1200:
                # Sub-split into sentences
                sentences = re.split(r"(?<=[.!?])\s+", chunk)
                current_accum: list[str] = []
                current_len = 0
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    if current_len + len(s_clean) > 800 and current_accum:
                        final_chunks.append(" ".join(current_accum))
                        current_accum = [s_clean]
                        current_len = len(s_clean)
                    else:
                        current_accum.append(s_clean)
                        current_len += len(s_clean)
                if current_accum:
                    final_chunks.append(" ".join(current_accum))
            else:
                final_chunks.append(chunk)

        # Build Clause models with stable IDs
        clause_counter = 1
        for chunk_text in final_chunks:
            # Skip trivial artifacts (< 15 characters, page number stamps)
            if len(chunk_text) < 15 and (chunk_text.isdigit() or "page" in chunk_text.lower()):
                continue

            c_id = f"{short_doc_id}-p{page_num}-c{clause_counter:02d}"
            clauses.append(
                Clause(
                    id=c_id,
                    doc_id=doc_id,
                    page=page_num,
                    text=chunk_text,
                )
            )
            clause_counter += 1

    return clauses


class BM25ClauseIndex:
    """In-memory BM25 index over extracted document clauses."""

    def __init__(self, clauses: List[Clause]) -> None:
        self.clauses = clauses
        self.clause_map: dict[str, Clause] = {c.id: c for c in clauses}
        self.corpus_tokens = [_tokenize(c.text) for c in clauses]

        if self.corpus_tokens and any(len(t) > 0 for t in self.corpus_tokens):
            self.bm25 = BM25Okapi(self.corpus_tokens)
        else:
            self.bm25 = None

    def get_by_id(self, clause_id: str) -> Optional[Clause]:
        """Look up clause by its stable ID."""
        return self.clause_map.get(clause_id)

    def get_all(self) -> List[Clause]:
        """Return all indexed clauses."""
        return list(self.clauses)

    def search(self, query: str, top_k: int = 5) -> List[Clause]:
        """Search clauses by query using BM25 ranking."""
        if not self.bm25 or not self.clauses:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return self.clauses[:top_k]

        doc_scores = self.bm25.get_scores(tokens)
        top_indices = sorted(
            range(len(doc_scores)),
            key=lambda i: doc_scores[i],
            reverse=True,
        )[:top_k]

        return [self.clauses[i] for i in top_indices if doc_scores[i] > 0]

