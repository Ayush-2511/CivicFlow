"""Gemini LLM Provider Implementation.

Adheres strictly to the LLM protocol. Handles structured JSON generation,
Pydantic validation, self-correcting retries, timeouts, and rate limits.
"""

import asyncio
import json
import logging
from typing import TypeVar
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.exceptions import ProviderError

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _clean_json_text(text: str) -> str:
    """Strip markdown code blocks if the model wrapped the JSON output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


class GeminiLLMProvider:
    """LLM Provider adapter backed by Google GenAI (Gemini)."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.MAX_RETRIES
        self._client = client

    def _get_client(self) -> genai.Client:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ProviderError(
                "GEMINI_API_KEY is not set. Please set it in .env or provide it directly."
            )
        self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _resolve_model(self, tier: str) -> str:
        """Map tier to configured model name."""
        if tier == "fast":
            return settings.MODEL_FAST
        return settings.MODEL_STRONG

    async def generate_text(
        self,
        prompt: str,
        *,
        tier: str = "fast",
        images: list[bytes] | None = None,
        system_instruction: str | None = None,
    ) -> str:
        """Generate raw text from prompt, with optional multimodal images."""
        client = self._get_client()
        model_name = self._resolve_model(tier)

        # Zero temperature for deterministic, reliable policy parsing
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
        )

        contents: list[str | types.Part] = []
        if images:
            for img_bytes in images:
                mime = "image/png" if img_bytes.startswith(b"\x89PNG") else "image/jpeg"
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
        contents.append(prompt)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    ),
                    timeout=self.timeout,
                )
                if not response.text:
                    raise ProviderError("LLM returned an empty response.")
                return response.text.strip()
            except asyncio.TimeoutError:
                if attempt == self.max_retries:
                    raise ProviderError(f"LLM request timed out after {self.timeout}s.")
                await asyncio.sleep(2 ** attempt)
            except APIError as e:
                if attempt == self.max_retries:
                    raise ProviderError(f"Gemini API error: {e.message}", details={"code": e.code})
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                if attempt == self.max_retries:
                    raise ProviderError(f"Unexpected LLM failure: {str(e)}")
                await asyncio.sleep(2 ** attempt)

        raise ProviderError("LLM generation failed after maximum retries.")

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        tier: str = "strong",
        images: list[bytes] | None = None,
        system_instruction: str | None = None,
    ) -> T:
        """Generate structured output validated against Pydantic schema with retry feedback."""
        client = self._get_client()
        model_name = self._resolve_model(tier)

        # Build contents (multimodal if images provided)
        contents: list[str | types.Part] = []
        if images:
            for idx, img_bytes in enumerate(images):
                # Infer png vs jpeg or default to jpeg
                mime = "image/png" if img_bytes.startswith(b"\x89PNG") else "image/jpeg"
                contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
        contents.append(prompt)

        # Zero temperature ensures reproducible, consistent outputs on every run
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            system_instruction=system_instruction,
            temperature=0.0,
        )

        current_prompt = prompt
        last_error_msg = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                # If retrying due to validation error, augment prompt with the specific error
                active_contents = contents.copy()
                if attempt > 1 and last_error_msg:
                    feedback_prompt = (
                        f"{current_prompt}\n\n"
                        f"CRITICAL: Your previous response failed schema validation with error:\n"
                        f"{last_error_msg}\n"
                        f"Ensure every required field is present and types match the schema exactly."
                    )
                    active_contents[-1] = feedback_prompt

                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=model_name,
                        contents=active_contents,
                        config=config,
                    ),
                    timeout=self.timeout,
                )

                if not response.text:
                    last_error_msg = "Model returned empty text."
                    continue

                cleaned_json = _clean_json_text(response.text)
                validated_obj = schema.model_validate_json(cleaned_json)
                return validated_obj

            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning(
                    "Validation error on attempt %d/%d: %s",
                    attempt,
                    self.max_retries,
                    str(e),
                )
                last_error_msg = str(e)
                if attempt == self.max_retries:
                    raise ProviderError(
                        f"Failed to generate structured data matching {schema.__name__}: {str(e)}",
                        details={"last_error": str(e), "attempts": attempt},
                    )
                await asyncio.sleep(1)

            except asyncio.TimeoutError:
                if attempt == self.max_retries:
                    raise ProviderError(f"LLM request timed out after {self.timeout}s.")
                await asyncio.sleep(2 ** attempt)

            except APIError as e:
                if attempt == self.max_retries:
                    raise ProviderError(f"Gemini API error: {e.message}", details={"code": e.code})
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                if attempt == self.max_retries:
                    raise ProviderError(f"Structured generation error: {str(e)}")
                await asyncio.sleep(2 ** attempt)

        raise ProviderError(f"Failed to produce valid {schema.__name__} after {self.max_retries} attempts.")
