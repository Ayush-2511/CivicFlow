"""Unit tests for document parsing node with PDF and OCR fallbacks."""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock
import pypdf
from app.exceptions import UnreadableDocument
from app.nodes.parse import parse_document


def create_sample_pdf_bytes(text: str) -> bytes:
    """Generate in-memory PDF with specified text."""
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # pypdf doesn't easily create text streams without complex objects,
    # so we test with a minimal valid PDF text structure or mock reader
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.asyncio
async def test_parse_corrupted_pdf_raises_unreadable_document():
    bad_pdf_bytes = b"%PDF-1.4 completely corrupted data cannot parse"
    with pytest.raises(UnreadableDocument):
        await parse_document(bad_pdf_bytes, "application/pdf")


@pytest.mark.asyncio
async def test_parse_empty_bytes_raises_unreadable_document():
    with pytest.raises(UnreadableDocument):
        await parse_document(b"", "application/pdf")


@pytest.mark.asyncio
async def test_parse_image_via_ocr_success():
    mock_llm = MagicMock()
    mock_transcription = (
        "1. Definitions: Small farmer means a farmer with land holding up to 2 hectares.\n"
        "2. Eligibility: All landholder farmer families having cultivable landholding."
    )
    mock_llm.generate_text = AsyncMock(return_value=mock_transcription)

    sample_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50
    pages = await parse_document(sample_png, "image/png", llm=mock_llm)

    assert len(pages) == 1
    assert pages[0].page == 1
    assert "Small farmer means a farmer with land holding up to 2 hectares" in pages[0].text
    assert mock_llm.generate_text.call_count == 1


@pytest.mark.asyncio
async def test_parse_image_illegible_raises_unreadable_document():
    mock_llm = MagicMock()
    mock_llm.generate_text = AsyncMock(return_value="[illegible]")

    sample_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50
    with pytest.raises(UnreadableDocument, match="blurry"):
        await parse_document(sample_jpg, "image/jpeg", llm=mock_llm)

