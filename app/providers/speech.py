"""TTS Provider Implementation using Edge-TTS with regional Indian voice mappings.

Adheres strictly to the TTS protocol.
"""

import logging
import edge_tts
from app.exceptions import ProviderError

logger = logging.getLogger(__name__)

# High-quality neural voices for Indian regional languages
VOICE_MAP: dict[str, str] = {
    "hi": "hi-IN-SwaraNeural",       # Hindi female
    "en": "en-IN-NeerjaNeural",      # Indian English female
    "mr": "mr-IN-AarohiNeural",      # Marathi female
    "ta": "ta-IN-PallaviNeural",     # Tamil female
    "te": "te-IN-ShrutiNeural",      # Telugu female
    "bn": "bn-IN-TanishaaNeural",    # Bengali female
    "gu": "gu-IN-DhwaniNeural",      # Gujarati female
    "kn": "kn-IN-SapnaNeural",       # Kannada female
    "ml": "ml-IN-SobhanaNeural",     # Malayalam female
    "ur": "ur-IN-GulNeural",         # Urdu female
}


class EdgeTTSProvider:
    """Text-to-Speech provider using Edge TTS neural voices."""

    def __init__(self, voice_map: dict[str, str] | None = None) -> None:
        self.voice_map = voice_map or VOICE_MAP

    def get_voice_for_language(self, language: str) -> str:
        """Resolve voice identifier for a given language code."""
        lang_code = language.lower().strip()
        # Fall back to Hindi if unknown
        return self.voice_map.get(lang_code, self.voice_map.get("hi", "hi-IN-SwaraNeural"))

    async def synthesize(self, text: str, language: str = "hi") -> bytes:
        """Synthesize text into MP3 audio bytes.

        Raises:
            ProviderError: if synthesis fails or output is empty.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ProviderError("Cannot synthesize empty text.")

        voice = self.get_voice_for_language(language)

        try:
            communicate = edge_tts.Communicate(text=clean_text, voice=voice)
            chunks: list[bytes] = []

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])

            audio_data = b"".join(chunks)
            if not audio_data:
                raise ProviderError(f"TTS synthesis produced empty audio for voice {voice}.")

            return audio_data

        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            logger.error("TTS synthesis error for language %s (%s): %s", language, voice, str(e))
            raise ProviderError(f"TTS synthesis failed: {str(e)}") from e

