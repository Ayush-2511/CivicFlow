"""Unit tests for SQLite DocumentStore."""

import tempfile
from pathlib import Path
from app.schemas import Clause
from app.store import DocumentStore


def test_document_store_save_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        store = DocumentStore(db_path=db_path)

        doc_id = "test_doc_12345"
        clauses = [
            Clause(id="test_d-p1-c01", doc_id=doc_id, page=1, text="Clause 1 text."),
            Clause(id="test_d-p1-c02", doc_id=doc_id, page=1, text="Clause 2 text."),
        ]

        assert not store.has_document(doc_id)
        assert store.get_clauses(doc_id) is None

        store.save_document(
            doc_id=doc_id,
            filename="policy.pdf",
            content_type="application/pdf",
            clauses=clauses,
        )

        assert store.has_document(doc_id)
        doc = store.get_document(doc_id)
        assert doc is not None
        assert doc["filename"] == "policy.pdf"

        saved_clauses = store.get_clauses(doc_id)
        assert saved_clauses is not None
        assert len(saved_clauses) == 2
        assert saved_clauses[0].id == "test_d-p1-c01"
        assert saved_clauses[1].text == "Clause 2 text."

