"""Document Ingestion Node.

Handles file uploads and URL retrieval, generates deterministic doc_id (SHA-256),
checks SQLite cache, and persists source files.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from app.config import settings
from app.exceptions import ProviderError
from app.providers.sources import sources_fetcher
from app.schemas import Clause
from app.store import store


@dataclass
class IngestResult:
    """Output contract of the ingestion node."""
    doc_id: str
    filename: str
    content_type: str
    raw_bytes: bytes
    file_path: Path
    is_cached: bool
    cached_clauses: Optional[List[Clause]] = None


def detect_content_type(raw_bytes: bytes, filename: str) -> str:
    """Infer content type using file magic bytes and extension."""
    if raw_bytes.startswith(b"%PDF-"):
        return "application/pdf"
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16]:
        return "image/webp"

    # HTML / web notice detection
    trimmed = raw_bytes.strip().lower()
    if trimmed.startswith((b"<!doctype html", b"<html", b"<?xml")):
        return "text/html"

    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in [".png"]:
        return "image/png"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext in [".webp"]:
        return "image/webp"
    if ext in [".txt", ".md"]:
        return "text/plain"
    if ext in [".html", ".htm"]:
        return "text/html"

    return "application/octet-stream"


async def ingest_document(
    *,
    file_bytes: bytes | None = None,
    filename: str = "document.pdf",
    url: str | None = None,
) -> IngestResult:
    """Ingest a policy document from raw bytes or an official URL.

    Raises:
        ProviderError: If URL retrieval fails or inputs are invalid.
    """
    if file_bytes is None and url is None:
        raise ProviderError("Either file_bytes or url must be provided for ingestion.")

    if url is not None and file_bytes is None:
        file_bytes, fetched_filename, _ = await sources_fetcher.fetch_document_by_url(url)
        if fetched_filename:
            filename = fetched_filename

    assert file_bytes is not None

    if len(file_bytes) == 0:
        raise ProviderError("Ingested document byte stream is empty.")

    # Compute deterministic SHA-256 identifier
    doc_id = hashlib.sha256(file_bytes).hexdigest()
    content_type = detect_content_type(file_bytes, filename)

    # Ensure safe filename
    safe_filename = Path(filename).name
    save_path = settings.UPLOAD_DIR / f"{doc_id[:12]}_{safe_filename}"
    if not save_path.exists():
        save_path.write_bytes(file_bytes)

    # Check SQLite cache
    cached_clauses = store.get_clauses(doc_id)
    is_cached = cached_clauses is not None and len(cached_clauses) > 0

    return IngestResult(
        doc_id=doc_id,
        filename=safe_filename,
        content_type=content_type,
        raw_bytes=file_bytes,
        file_path=save_path,
        is_cached=is_cached,
        cached_clauses=cached_clauses if is_cached else None,
    )
