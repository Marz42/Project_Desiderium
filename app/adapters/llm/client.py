"""OpenAI-compatible chat completions HTTP client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LlmClientError(RuntimeError):
    """Raised when the LLM HTTP API returns an error."""


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("LLM API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        url = f"{self._base_url}/chat/completions"
        response = await self._client.post(url, json=payload)
        if response.status_code >= 400:
            body = response.text[:500]
            raise LlmClientError(f"LLM API error {response.status_code}: {body}")

        data = response.json()
        if not isinstance(data, dict):
            raise LlmClientError("LLM API returned non-object response")
        return data
