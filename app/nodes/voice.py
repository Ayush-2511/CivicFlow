"""Voice Synthesis Node.

Synthesizes audio per explainer segment concurrently using regional neural TTS,
persists audio files to the cache directory, and links audio URLs.
"""

import asyncio
import logging
from typing import List
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

    short_id = doc_id[:10]
    filename = f"{short_id}_seg_{idx:02d}.mp3"
    file_path = settings.AUDIO_OUTPUT_DIR / filename

    try:
        # Check if already cached on disk
        if not file_path.exists():
            audio_bytes = await tts.synthesize(clean_text, language=language)
            file_path.write_bytes(audio_bytes)

        url = f"/audio/{filename}"
        segment.audio_url = url
        return url

    except Exception as e:
        logger.error("Failed to synthesize segment %d (%s): %s", idx, language, str(e))
        # Keep pipeline running even if one non-critical audio segment fails
        return ""


async def synthesize_explainer_voice(
    explainer: Explainer,
    doc_id: str,
    tts: TTS,
) -> Explainer:
    """Synthesize voice audio for all explainer segments in parallel.

    Updates each Segment with its audio_url and populates explainer.audio_urls.
    """
    if not explainer.segments:
        return explainer

    tasks = [
        _synthesize_single_segment(
            segment=seg,
            idx=idx,
            doc_id=doc_id,
            language=explainer.language,
            tts=tts,
        )
        for idx, seg in enumerate(explainer.segments)
    ]

    audio_urls: List[str] = await asyncio.gather(*tasks)
    explainer.audio_urls = [url for url in audio_urls if url]

    return explainer

