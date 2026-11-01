"""Official Government Sources Fetcher.

Provides live retrieval of policy documents, gazettes, and PIB releases.
Supports live URLs from e-Gazette, PIB, myScheme, and ministry portals.
"""

import logging
import re
from pathlib import Path
from urllib.parse import urlparse
import httpx
from app.exceptions import ProviderError

logger = logging.getLogger(__name__)

# Sample verified official sources for live demos
VERIFIED_GOV_SOURCES = [
    {
        "title": "PM Kisan Samman Nidhi Operational Guidelines",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
        "url": "https://pmkisan.gov.in/Documents/RevisedPM-KISANOperationalGuidelines(English).pdf",
        "category": "agriculture",
    },
    {
        "title": "Credit Guarantee Scheme for Micro and Small Enterprises",
        "ministry": "Ministry of Micro, Small and Medium Enterprises",
        "url": "https://www.cgtmse.in/Default/ViewFile/?id=1658406144869_Circular%20no.%20199%20-%20CGTMSE%20scheme%20documents.pdf&path=Page",
        "category": "msme",
    },
]


class OfficialSourceFetcher:
    """Fetches official government notifications, gazettes, and press releases."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout = timeout_seconds

    async def fetch_document_by_url(self, url: str) -> tuple[bytes, str, str]:
        """Download document from a public official URL.

        Returns:
            Tuple of (raw_bytes, filename, content_type)
        Raises:
            ProviderError: If the URL cannot be fetched or returns a non-200 code.
        """
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ProviderError(f"Invalid official URL: {url}")

        filename = Path(parsed.path).name or "document.pdf"
        # Sanitize filename
        filename = re.sub(r"[^\w\.-]", "_", filename)

        headers = {
            "User-Agent": "CivicFlow-PolicyExplainer/0.1 (+https://github.com/Ayush-2511/CivicFlow)"
        }

        async def _do_fetch(verify: bool) -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=verify) as client:
                return await client.get(url, headers=headers)

        try:
            try:
                response = await _do_fetch(verify=True)
            except httpx.ConnectError as e:
                # Many Indian government portals (.gov.in, .nic.in) use national CAs (e.g. NIC/CCA)
                # that are not in standard Python/certifi trust stores. Retry with verify=False.
                err_msg = str(e).lower()
                if "certificate_verify_failed" in err_msg or "certificate verify failed" in err_msg:
                    logger.warning(
                        "SSL certificate verification failed for official portal %s. Retrying with insecure transport for government domain...",
                        url,
                    )
                    response = await _do_fetch(verify=False)
                else:
                    raise

            if response.status_code != 200:
                raise ProviderError(
                    f"Failed to fetch document from {url}: HTTP {response.status_code}",
                    details={"status_code": response.status_code, "url": url},
                )

            content_type = response.headers.get("content-type", "application/pdf").split(";")[0].strip()
            content = response.content

            if not content:
                raise ProviderError(f"Remote document from {url} is empty.")

            return content, filename, content_type

        except httpx.RequestError as e:
            logger.error("HTTP request failed for URL %s: %s", url, str(e))
            raise ProviderError(f"Network error fetching official document: {str(e)}") from e

    def get_verified_demo_sources(self) -> list[dict]:
        """Return list of verified official government sources for live demonstrations."""
        return list(VERIFIED_GOV_SOURCES)


sources_fetcher = OfficialSourceFetcher()

