"""Unit tests for GroqLLMProvider."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from pydantic import BaseModel

from app.exceptions import ProviderError
from app.providers.base import LLM
from app.providers.groq import GroqLLMProvider


class SampleExtraction(BaseModel):
    title: str
    count: int


def test_groq_protocol_conformance():
    provider = GroqLLMProvider(api_key="mock_key")
    assert isinstance(provider, LLM)


@pytest.mark.asyncio
async def test_groq_missing_api_key_raises_provider_error():
    provider = GroqLLMProvider(api_key="")
    with pytest.raises(ProviderError, match="GROQ_API_KEY is not set"):
        await provider.generate_text("Hi")


@pytest.mark.asyncio
async def test_groq_generate_text_success():
    provider = GroqLLMProvider(api_key="mock_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from Groq LPU!"}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        text = await provider.generate_text("Say hi", tier="fast")
        assert text == "Hello from Groq LPU!"


@pytest.mark.asyncio
async def test_groq_generate_structured_success():
    provider = GroqLLMProvider(api_key="mock_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"title": "PM Kisan", "count": 6000})}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.generate_structured("Extract scheme", SampleExtraction)
        assert isinstance(result, SampleExtraction)
        assert result.title == "PM Kisan"
        assert result.count == 6000


@pytest.mark.asyncio
async def test_groq_generate_structured_retries_on_invalid_json():
    provider = GroqLLMProvider(api_key="mock_key", max_retries=2)

    # Attempt 1: Invalid JSON (missing count field)
    resp_fail = MagicMock()
    resp_fail.status_code = 200
    resp_fail.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"title": "Incomplete"})}}]
    }
    resp_fail.raise_for_status = MagicMock()

    # Attempt 2: Valid JSON
    resp_success = MagicMock()
    resp_success.status_code = 200
    resp_success.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"title": "Fixed", "count": 42})}}]
    }
    resp_success.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[resp_fail, resp_success]):
        result = await provider.generate_structured("Extract", SampleExtraction)
        assert result.title == "Fixed"
        assert result.count == 42


@pytest.mark.asyncio
async def test_groq_exhausts_retries_raises_provider_error():
    provider = GroqLLMProvider(api_key="mock_key", max_retries=2)
    resp_fail = MagicMock()
    resp_fail.status_code = 200
    resp_fail.json.return_value = {
        "choices": [{"message": {"content": "not-valid-json"}}]
    }
    resp_fail.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp_fail):
        with pytest.raises(ProviderError, match="Failed to generate structured data"):
            await provider.generate_structured("Extract", SampleExtraction)

