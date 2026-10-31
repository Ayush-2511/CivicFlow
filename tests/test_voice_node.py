"""Unit tests for the voice synthesis node and static audio serving."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.nodes.voice import synthesize_explainer_voice
from app.schemas import Explainer, Segment

client = TestClient(app)


@pytest.mark.asyncio
async def test_synthesize_explainer_voice_parallel():
    explainer = Explainer(
        language="hi",
        segments=[
            Segment(text="पहला वाक्य।", clause_ids=["c1"]),
            Segment(text="दूसरा वाक्य।", clause_ids=["c2"]),
        ],
        checklist=["दस्तावेज़"],
    )

    mock_tts = MagicMock()
    mock_audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00#TSSE\x00\x00\x00\x0f\x00\x00\x03Lavf58.29.100\x00" + b"\x00" * 200
    mock_tts.synthesize = AsyncMock(return_value=mock_audio_bytes)

    doc_id = "test_doc_voice_123"
    result = await synthesize_explainer_voice(explainer, doc_id=doc_id, tts=mock_tts)

    assert len(result.audio_urls) == 2
    assert result.segments[0].audio_url is not None
    assert result.segments[1].audio_url is not None
    assert "/audio/" in result.segments[0].audio_url
    assert mock_tts.synthesize.call_count == 2

    # Verify that the generated file is actually served by FastAPI /audio endpoint
    audio_path = result.segments[0].audio_url
    response = client.get(audio_path)
    assert response.status_code == 200
    assert len(response.content) == len(mock_audio_bytes)

