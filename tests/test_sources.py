"""Unit tests for OfficialSourceFetcher."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.exceptions import ProviderError
from app.providers.sources import OfficialSourceFetcher


def test_verified_sources_list():
    fetcher = OfficialSourceFetcher()
    sources = fetcher.get_verified_demo_sources()
    assert len(sources) >= 2
    assert any("PM Kisan" in s["title"] for s in sources)


@pytest.mark.asyncio
async def test_fetch_invalid_url_raises_provider_error():
    fetcher = OfficialSourceFetcher()
    with pytest.raises(ProviderError, match="Invalid official URL"):
        await fetch_document_by_url_helper(fetcher, "not-a-valid-url")


async def fetch_document_by_url_helper(fetcher: OfficialSourceFetcher, url: str):
    return await fetcher.fetch_document_by_url(url)


@pytest.mark.asyncio
async def test_fetch_document_by_url_success():
    fetcher = OfficialSourceFetcher()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"%PDF-1.4 official government notification bytes"
    mock_response.headers = {"content-type": "application/pdf"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        content, filename, content_type = await fetcher.fetch_document_by_url("https://pmkisan.gov.in/test.pdf")

        assert content == b"%PDF-1.4 official government notification bytes"
        assert filename == "test.pdf"
        assert content_type == "application/pdf"

