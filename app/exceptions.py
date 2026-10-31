"""Typed domain and provider exceptions for CivicFlow.

Rule: Raise typed errors; never use bare exceptions.
"""


class CivicFlowError(Exception):
    """Base exception for all CivicFlow custom exceptions."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ProviderError(CivicFlowError):
    """Raised when an external provider (LLM, TTS, OCR) fails, times out, or exhausts retries."""
    pass


class UnreadableDocument(CivicFlowError):
    """Raised when a document cannot be parsed (e.g. blurry scan, rotated image, empty text)."""
    pass


class NotAPolicy(CivicFlowError):
    """Raised when an ingested document is not a government policy, scheme, or legal act."""
    pass

