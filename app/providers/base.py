"""Provider protocols (interfaces) for LLM and Speech services.

All pipeline nodes interact only with these protocols.
"""

from typing import Protocol, TypeVar, runtime_checkable
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLM(Protocol):
    """Protocol for Large Language Model operations with structured output and retries."""

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        tier: str = "strong",
        images: list[bytes] | None = None,
        system_instruction: str | None = None,
    ) -> T:
        """Generate structured output validated against a Pydantic schema with retry on failure."""
        ...

    async def generate_text(
        self,
        prompt: str,
        *,
        tier: str = "fast",
        system_instruction: str | None = None,
    ) -> str:
        """Generate plain text completion."""
        ...


@runtime_checkable
class TTS(Protocol):
    """Protocol for Text-To-Speech synthesis across regional languages."""

    async def synthesize(self, text: str, language: str) -> bytes:
        """Synthesize text into audio bytes (MP3) in the requested language."""
        ...

