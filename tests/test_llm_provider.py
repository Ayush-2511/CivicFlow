"""Unit tests for GeminiLLMProvider using mock clients to test retries, validation and timeouts."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel, Field

from app.exceptions import ProviderError
from app.providers.base import LLM
from app.providers.llm import GeminiLLMProvider, _clean_json_text


class SampleModel(BaseModel):
    name: str
    amount: float
    is_active: bool = True


def test_clean_json_text():
    wrapped = "```json\n{\"name\": \"test\", \"amount\": 100.0}\n```"
    assert _clean_json_text(wrapped) == "{\"name\": \"test\", \"amount\": 100.0}"

    plain = "{\"name\": \"plain\", \"amount\": 50.0}"
    assert _clean_json_text(plain) == plain


def test_llm_protocol_conformance():
    provider = GeminiLLMProvider(api_key="mock_key")
    assert isinstance(provider, LLM)


@pytest.mark.asyncio
async def test_generate_structured_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"name": "PM Kisan", "amount": 6000.0, "is_active": true}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    provider = GeminiLLMProvider(client=mock_client, max_retries=2)
    result = await provider.generate_structured("Extract scheme info", SampleModel)

    assert isinstance(result, SampleModel)
    assert result.name == "PM Kisan"
    assert result.amount == 6000.0
    assert mock_client.aio.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_retries_on_invalid_json():
    mock_client = MagicMock()
    # First call returns invalid schema JSON (amount is invalid type), second call returns valid JSON
    bad_response = MagicMock()
    bad_response.text = '{"name": "Invalid", "amount": "not_a_number"}'

    good_response = MagicMock()
    good_response.text = '{"name": "Valid", "amount": 500.0, "is_active": true}'

    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=[bad_response, good_response]
    )

    provider = GeminiLLMProvider(client=mock_client, max_retries=3)
    result = await provider.generate_structured("Extract scheme info", SampleModel)

    assert isinstance(result, SampleModel)
    assert result.name == "Valid"
    assert result.amount == 500.0
    assert mock_client.aio.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_generate_structured_exhausts_retries_raises_provider_error():
    mock_client = MagicMock()
    bad_response = MagicMock()
    bad_response.text = '{"corrupted": true}'
    mock_client.aio.models.generate_content = AsyncMock(return_value=bad_response)

    provider = GeminiLLMProvider(client=mock_client, max_retries=2)
    with pytest.raises(ProviderError, match="Failed to generate structured data matching SampleModel"):
        await provider.generate_structured("Extract info", SampleModel)

    assert mock_client.aio.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_generate_text_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello, world!"
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    provider = GeminiLLMProvider(client=mock_client, max_retries=2)
    text = await provider.generate_text("Say hello")
    assert text == "Hello, world!"

