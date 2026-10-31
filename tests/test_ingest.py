"""Unit tests for document ingestion node."""

import uuid
import pytest
from app.exceptions import ProviderError
from app.nodes.ingest import detect_content_type, ingest_document
from app.schemas import Clause
from app.store import store


def test_detect_content_type():
    assert detect_content_type(b"%PDF-1.4...", "doc.pdf") == "application/pdf"
    assert detect_content_type(b"\x89PNG\r\n\x1a\n...", "image.png") == "image/png"
    assert detect_content_type(b"\xff\xd8\xff\xe0...", "photo.jpg") == "image/jpeg"
    assert detect_content_type(b"RIFF\x00\x00\x00\x00WEBP...", "photo.webp") == "image/webp"
    assert detect_content_type(b"generic text", "doc.pdf") == "application/pdf"


@pytest.mark.asyncio
async def test_ingest_document_success():
    unique_marker = uuid.uuid4().hex.encode()
    sample_bytes = b"%PDF-1.5 Sample test content: " + unique_marker
    result = await ingest_document(file_bytes=sample_bytes, filename="pmkisan.pdf")

    assert result.doc_id is not None
    assert len(result.doc_id) == 64  # SHA-256
    assert result.filename == "pmkisan.pdf"
    assert result.content_type == "application/pdf"
    assert result.file_path.exists()


@pytest.mark.asyncio
async def test_ingest_document_cache_hit():
    unique_marker = uuid.uuid4().hex.encode()
    sample_bytes = b"%PDF-1.5 Distinct content for cache verification: " + unique_marker
    result1 = await ingest_document(file_bytes=sample_bytes, filename="cache_test.pdf")
    assert not result1.is_cached

    # Save mock clauses to store under this doc_id
    clauses = [Clause(id=f"{result1.doc_id[:6]}-p1-c01", doc_id=result1.doc_id, page=1, text="Test clause")]
    store.save_document(result1.doc_id, "cache_test.pdf", "application/pdf", clauses)

    # Ingesting the same bytes again should detect the cache hit
    result2 = await ingest_document(file_bytes=sample_bytes, filename="cache_test.pdf")
    assert result2.is_cached
    assert result2.cached_clauses is not None
    assert len(result2.cached_clauses) == 1


@pytest.mark.asyncio
async def test_ingest_empty_bytes_raises_error():
    with pytest.raises(ProviderError, match="empty"):
        await ingest_document(file_bytes=b"")
