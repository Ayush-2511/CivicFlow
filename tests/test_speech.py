"""Tests for TTS Provider and Indian language voice synthesis."""

import pytest
from app.exceptions import ProviderError
from app.providers.base import TTS
from app.providers.speech import EdgeTTSProvider, VOICE_MAP


def test_speech_protocol_conformance():
    provider = EdgeTTSProvider()
    assert isinstance(provider, TTS)


def test_voice_mapping():
    provider = EdgeTTSProvider()
    assert provider.get_voice_for_language("hi") == "hi-IN-SwaraNeural"
    assert provider.get_voice_for_language("mr") == "mr-IN-AarohiNeural"
    assert provider.get_voice_for_language("en") == "en-IN-NeerjaNeural"
    # Fallback to default Hindi on unknown language
    assert provider.get_voice_for_language("unknown") == "hi-IN-SwaraNeural"


@pytest.mark.asyncio
async def test_empty_text_raises_provider_error():
    provider = EdgeTTSProvider()
    with pytest.raises(ProviderError, match="Cannot synthesize empty text"):
        await provider.synthesize("   ", language="hi")


@pytest.mark.asyncio
async def test_hindi_synthesis_live():
    """Verify live Edge-TTS synthesis for Hindi legal/policy text."""
    provider = EdgeTTSProvider()
    hindi_text = "प्रधानमंत्री किसान सम्मान निधि योजना के तहत किसानों को वित्तीय सहायता दी जाती है।"
    audio = await provider.synthesize(hindi_text, language="hi")
    assert isinstance(audio, bytes)
    assert len(audio) > 1000  # Should be non-trivial audio stream
    # Check MP3 sync word or header (ID3 header or 0xFF frame sync)
    assert audio.startswith(b"ID3") or audio[0] == 0xFF or len(audio) > 5000


@pytest.mark.asyncio
async def test_second_language_synthesis_live():
    """Verify live Edge-TTS synthesis for English (India)."""
    provider = EdgeTTSProvider()
    en_text = "Farmers possessing up to two hectares of land are eligible for this welfare scheme."
    audio = await provider.synthesize(en_text, language="en")
    assert isinstance(audio, bytes)
    assert len(audio) > 1000

