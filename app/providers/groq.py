"""Groq LLM Provider Implementation.

Adheres strictly to the LLM protocol. Backed by Groq's high-speed LPU inference engine,
using OpenAI-compatible endpoints with structured JSON parsing, Pydantic validation,
compact token formatting, and dynamic multi-model rate-limit rotation.
"""

import asyncio
import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional, TypeVar
import httpx
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


class GroqLLMProvider:
    """LLM Provider adapter backed by Groq with multi-model rate-limit rotation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else max(settings.MAX_RETRIES, 5)
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self._request_counter = 0

    def _get_model_pool(self, tier: str, has_images: bool = False) -> List[str]:
        """Return prioritized model pool with separate token rate-limit buckets."""
        if has_images:
            return ["llama-3.2-11b-vision-preview"]
        if tier == "fast":
            pool = [settings.GROQ_MODEL_FAST, settings.GROQ_MODEL_STRONG]
        else:
            pool = [settings.GROQ_MODEL_STRONG, settings.GROQ_MODEL_FAST]
        return [m for m in dict.fromkeys(pool) if m]

    def _resolve_model(self, tier: str, has_images: bool = False, model_idx: int = 0) -> str:
        """Map tier and pool index to configured Groq model name."""
        pool = self._get_model_pool(tier, has_images)
        return pool[model_idx % len(pool)]

    def _get_headers(self) -> Dict[str, str]:
        key = self.api_key
        if not key:
            raise ProviderError(
                "GROQ_API_KEY is not set. Please get a free key from https://console.groq.com/keys and set it in .env."
            )
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "CivicFlow-PolicyExplainer/0.1",
        }

    async def generate_text(
        self,
        prompt: str,
        *,
        tier: str = "fast",
        images: Optional[List[bytes]] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generate plain text completion from prompt, with model rotation on 429."""
        headers = self._get_headers()
        model_pool = self._get_model_pool(tier, has_images=bool(images))
        model_idx = self._request_counter
        self._request_counter += 1
        endpoint = f"{self.base_url}/chat/completions"

        messages: List[Dict[str, Any]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        if images:
            user_content: List[Dict[str, Any]] = []
            for img_bytes in images:
                mime = "image/png" if img_bytes.startswith(b"\x89PNG") else "image/jpeg"
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
            user_content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": prompt})

        for attempt in range(1, self.max_retries + 1):
            current_model = model_pool[model_idx % len(model_pool)]
            payload = {
                "model": current_model,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 1500,
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(endpoint, headers=headers, json=payload)

                    if resp.status_code == 401:
                        raise ProviderError("Groq API error: Unauthorized. Check GROQ_API_KEY in .env.")

                    if resp.status_code == 429:
                        err_text = resp.text
                        logger.warning(
                            "Groq rate limit (429) on model '%s' (attempt %d/%d). Text: %s",
                            current_model,
                            attempt,
                            self.max_retries,
                            err_text[:120],
                        )
                        # Switch to alternate model in pool if available
                        if model_idx + 1 < len(model_pool):
                            model_idx += 1
                            logger.info("Switching to alternate Groq model: %s", model_pool[model_idx % len(model_pool)])
                            await asyncio.sleep(0.5)
                            continue

                        wait_time = 2.0
                        retry_header = resp.headers.get("retry-after")
                        if retry_header:
                            try:
                                wait_time = float(retry_header)
                            except ValueError:
                                pass
                        else:
                            m = re.search(r"try again in (\d+(?:\.\d+)?)s", err_text)
                            if m:
                                wait_time = float(m.group(1))

                        if attempt == self.max_retries:
                            raise ProviderError(f"Groq API rate limit exceeded across all models: {err_text}")
                        await asyncio.sleep(min(wait_time + 0.5, 30.0))
                        model_idx = 0
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices or not choices[0].get("message", {}).get("content"):
                        raise ProviderError("Groq returned an empty response.")

                    return choices[0]["message"]["content"].strip()

            except httpx.TimeoutException:
                if attempt == self.max_retries:
                    raise ProviderError(f"Groq request timed out after {self.timeout}s.")
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                err_detail = e.response.text
                if attempt == self.max_retries:
                    raise ProviderError(f"Groq HTTP error {e.response.status_code}: {err_detail}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                if attempt == self.max_retries:
                    raise ProviderError(f"Unexpected Groq failure: {str(e)}")
                await asyncio.sleep(2 ** attempt)

        raise ProviderError("Groq text generation failed after maximum retries.")

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        tier: str = "strong",
        images: Optional[List[bytes]] = None,
        system_instruction: Optional[str] = None,
    ) -> T:
        """Generate structured output validated against Pydantic schema with model rotation."""
        headers = self._get_headers()
        model_pool = self._get_model_pool(tier, has_images=bool(images))
        model_idx = self._request_counter
        self._request_counter += 1
        endpoint = f"{self.base_url}/chat/completions"

        # Compact JSON schema minimizes token overhead
        schema_json = json.dumps(schema.model_json_schema(), separators=(',', ':'))
        system_content = (
            (system_instruction or "You are a precise legal data extraction assistant.")
            + f"\n\nReturn ONLY a valid JSON object matching this JSON Schema:\n{schema_json}"
        )

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]

        if images:
            user_content: List[Dict[str, Any]] = []
            for img_bytes in images:
                mime = "image/png" if img_bytes.startswith(b"\x89PNG") else "image/jpeg"
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
            user_content.append({"type": "text", "text": prompt})
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": prompt})

        last_error_msg = ""

        for attempt in range(1, self.max_retries + 1):
            active_messages = [dict(m) for m in messages]
            current_model = model_pool[model_idx % len(model_pool)]

            if attempt > 1 and last_error_msg:
                # Self-correcting retry prompt
                active_messages.append({
                    "role": "user",
                    "content": (
                        f"CRITICAL: Your previous JSON response failed Pydantic validation with error:\n"
                        f"{last_error_msg}\n"
                        f"Ensure every required field is present and types match the schema exactly. Output ONLY valid JSON."
                    ),
                })

            payload = {
                "model": current_model,
                "messages": active_messages,
                "temperature": 0.0,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(endpoint, headers=headers, json=payload)

                    if resp.status_code == 401:
                        raise ProviderError("Groq API error: Unauthorized. Check GROQ_API_KEY in .env.")

                    if resp.status_code == 429:
                        err_text = resp.text
                        logger.warning(
                            "Groq rate limit (429) on model '%s' (attempt %d/%d). Text: %s",
                            current_model,
                            attempt,
                            self.max_retries,
                            err_text[:120],
                        )
                        # Switch to alternate model in pool if available
                        if model_idx + 1 < len(model_pool):
                            model_idx += 1
                            logger.info("Switching to alternate Groq model: %s", model_pool[model_idx % len(model_pool)])
                            await asyncio.sleep(0.5)
                            continue

                        wait_time = 2.0
                        retry_header = resp.headers.get("retry-after")
                        if retry_header:
                            try:
                                wait_time = float(retry_header)
                            except ValueError:
                                pass
                        else:
                            m = re.search(r"try again in (\d+(?:\.\d+)?)s", err_text)
                            if m:
                                wait_time = float(m.group(1))

                        if attempt == self.max_retries:
                            raise ProviderError(f"Groq API rate limit exceeded across all models: {err_text}")
                        await asyncio.sleep(min(wait_time + 0.5, 30.0))
                        model_idx = 0
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices or not choices[0].get("message", {}).get("content"):
                        raise ProviderError("Groq returned an empty JSON response.")

                    raw_text = choices[0]["message"]["content"]
                    cleaned_text = _clean_json_text(raw_text)

                    # Validate against Pydantic schema
                    parsed_obj = schema.model_validate_json(cleaned_text)
                    return parsed_obj

            except (ValidationError, json.JSONDecodeError) as val_err:
                last_error_msg = str(val_err)
                logger.warning(
                    "Groq response failed schema validation (attempt %d/%d): %s",
                    attempt,
                    self.max_retries,
                    last_error_msg,
                )
                if attempt == self.max_retries:
                    raise ProviderError(
                        f"Failed to generate structured data matching {schema.__name__} after {self.max_retries} attempts: {last_error_msg}",
                        details={"schema": schema.__name__, "last_error": last_error_msg},
                    )
                await asyncio.sleep(1)

            except httpx.TimeoutException:
                if attempt == self.max_retries:
                    raise ProviderError(f"Groq structured generation timed out after {self.timeout}s.")
                await asyncio.sleep(2 ** attempt)

            except httpx.HTTPStatusError as e:
                err_detail = e.response.text
                if attempt == self.max_retries:
                    raise ProviderError(f"Groq HTTP error {e.response.status_code}: {err_detail}")
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                if attempt == self.max_retries:
                    raise ProviderError(f"Unexpected Groq structured generation failure: {str(e)}")
                await asyncio.sleep(2 ** attempt)

        raise ProviderError("Groq structured generation failed after maximum retries.")
