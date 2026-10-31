"""Document Parsing Node.

Implements smart-order extraction:
1. Native digital PDF text layer (instant, free)
2. Vision LLM OCR fallback for scanned PDFs
3. Direct Vision LLM OCR for camera photos and images
4. Quality gate raising UnreadableDocument on blurry or empty inputs
"""

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List
import pypdf
from app.exceptions import UnreadableDocument
from app.providers.base import LLM

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    """Represents verbatim text extracted from a document page."""
    page: int
    text: str


def _load_prompt(filename: str) -> str:
    """Load prompt template from app/prompts."""
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Required prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


async def parse_document(
    raw_bytes: bytes,
    content_type: str,
    llm: LLM | None = None,
) -> List[PageText]:
    """Parse document bytes into a sequence of PageText objects.

    Raises:
        UnreadableDocument: If text layer is absent/degraded and OCR fails or yields illegible output.
    """
    if not raw_bytes or len(raw_bytes) < 10:
        raise UnreadableDocument("Document byte stream is empty or too small.")

    # 0. Plain text format (.txt, .md)
    if content_type == "text/plain":
        try:
            text = raw_bytes.decode("utf-8").strip()
            if len(text) < 20:
                raise UnreadableDocument("Text document is too short or empty.")
            return [PageText(page=1, text=text)]
        except UnicodeDecodeError as e:
            raise UnreadableDocument(f"Could not decode text document: {str(e)}") from e

    # 1. Digital PDF parsing
    if content_type == "application/pdf" or raw_bytes.startswith(b"%PDF-"):
        try:
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
        except Exception as e:
            raise UnreadableDocument(f"Corrupted or invalid PDF format: {str(e)}") from e

        if len(reader.pages) == 0:
            raise UnreadableDocument("PDF document contains no pages.")

        pages: List[PageText] = []
        total_chars = 0

        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            clean_text = "\n".join(
                line.strip() for line in page_text.splitlines() if line.strip()
            )
            pages.append(PageText(page=page_idx, text=clean_text))
            total_chars += len(clean_text)

        # Check if text layer is sufficient (> 50 chars total)
        if total_chars >= 50:
            return pages

        # 2. Scanned PDF fallback via OCR
        logger.info("PDF text layer empty/sparse (%d chars). Falling back to OCR.", total_chars)
        if llm is None:
            raise UnreadableDocument(
                "PDF has no digital text layer and no OCR engine was provided."
            )

        ocr_prompt = _load_prompt("ocr.md")
        ocr_pages: List[PageText] = []

        for page_idx, page in enumerate(reader.pages, start=1):
            image_bytes_list: list[bytes] = []
            for img in page.images:
                image_bytes_list.append(img.data)

            if image_bytes_list:
                text = await llm.generate_text(
                    prompt="Transcribe the attached policy document page verbatim.",
                    images=image_bytes_list[:3],  # Up to 3 images per page
                    system_instruction=ocr_prompt,
                    tier="fast",
                )
                clean_text = text.strip()
                if clean_text and clean_text != "[illegible]":
                    ocr_pages.append(PageText(page=page_idx, text=clean_text))

        if ocr_pages and sum(len(p.text) for p in ocr_pages) >= 50:
            return ocr_pages

        raise UnreadableDocument(
            "Scanned PDF could not be transcribed. The document appears blurry, blank, or degraded."
        )

    # 3. Direct image parsing (photos, scans)
    if content_type.startswith("image/") or raw_bytes.startswith((b"\x89PNG", b"\xff\xd8\xff")):
        if llm is None:
            raise UnreadableDocument("Vision OCR engine required to parse image documents.")

        ocr_prompt = _load_prompt("ocr.md")
        try:
            transcribed_text = await llm.generate_text(
                prompt="Transcribe all visible clauses and text from this document image.",
                images=[raw_bytes],
                system_instruction=ocr_prompt,
                tier="fast",
            )
        except Exception as e:
            raise UnreadableDocument(f"OCR processing failed for image: {str(e)}") from e

        cleaned = transcribed_text.strip()
        if not cleaned or len(cleaned) < 30 or cleaned.lower() == "[illegible]":
            raise UnreadableDocument(
                "Uploaded image is too blurry, dark, or illegible to transcribe. Please take a clearer photo."
            )

        return [PageText(page=1, text=cleaned)]

    raise UnreadableDocument(f"Unsupported document content type: '{content_type}'")

