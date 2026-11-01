"""Voice Synthesis Node.

Synthesizes audio per explainer segment concurrently using regional neural TTS,
persists audio files to the cache directory, and links audio URLs.
"""

import asyncio
import hashlib
import logging
from typing import List, Optional
from app.config import settings
from app.exceptions import ProviderError
from app.providers.base import TTS
from app.schemas import Explainer, Segment

logger = logging.getLogger(__name__)


async def _synthesize_single_segment(
    segment: Segment,
    idx: int,
    doc_id: str,
    language: str,
    tts: TTS,
) -> str:
    """Synthesize speech for a single segment and save to audio cache."""
    clean_text = segment.text.strip()
    if not clean_text:
        return ""

    short_id = (doc_id or "doc")[:10]
    lang = (language or "hi").lower().strip()
    # Content-addressed hash ensures no stale collisions across languages or text updates
    text_hash = hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:8]
    filename = f"{short_id}_{lang}_seg_{idx:02d}_{text_hash}.mp3"
    file_path = settings.AUDIO_OUTPUT_DIR / filename

    try:
        # Check if already cached on disk and non-empty
        if not file_path.exists() or file_path.stat().st_size == 0:
            logger.info("Synthesizing audio segment %d in %s (%d chars)...", idx, lang, len(clean_text))
            audio_bytes = await tts.synthesize(clean_text, language=lang)
            file_path.write_bytes(audio_bytes)
        else:
            logger.info("Using cached audio segment %d for %s: %s", idx, lang, filename)

        url = f"/audio/{filename}"
        segment.audio_url = url
        return url

    except Exception as e:
        logger.error("Failed to synthesize segment %d (%s): %s", idx, lang, str(e), exc_info=True)
        # Keep pipeline running even if one non-critical audio segment fails
        return ""


async def synthesize_explainer_voice(
    explainer: Explainer,
    doc_id: str,
    tts: TTS,
    language: Optional[str] = None,
) -> Explainer:
    """Synthesize voice audio for all explainer segments in parallel.

    Updates each Segment with its audio_url and populates explainer.audio_urls.
    """
    if not explainer.segments:
        return explainer

    target_lang = (language or explainer.language or "hi").lower().strip()

    tasks = [
        _synthesize_single_segment(
            segment=seg,
            idx=idx,
            doc_id=doc_id,
            language=target_lang,
            tts=tts,
        )
        for idx, seg in enumerate(explainer.segments)
    ]

    audio_urls: List[str] = await asyncio.gather(*tasks)
    explainer.audio_urls = [url for url in audio_urls if url]

    return explainer
