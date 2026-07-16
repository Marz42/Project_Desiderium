"""LLM adapter with JSON Schema output, retry, timeout, and token tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.adapters.llm.client import LlmClientError, OpenAICompatibleClient
from app.schemas.semantic import LlmUsageStats
from app.services.llm_config import LlmConfig, PromptTemplate, get_llm_config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LlmAdapterError(RuntimeError):
    """Raised when LLM structured output cannot be produced."""


_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


class LlmAdapter:
    def __init__(
        self,
        client: OpenAICompatibleClient,
        config: LlmConfig | None = None,
    ) -> None:
        self._client = client
        self._config = config or get_llm_config()
        self.usage = LlmUsageStats()

    async def close(self) -> None:
        await self._client.close()

    @staticmethod
    def render_prompt(template: PromptTemplate, variables: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key not in variables:
                raise LlmAdapterError(f"missing prompt variable: {key}")
            value = variables[key]
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False, indent=2)
            return str(value)

        return _PLACEHOLDER_RE.sub(replace, template.user_template)

    async def complete_structured(
        self,
        prompt: PromptTemplate,
        variables: dict[str, Any],
        result_model: type[T],
        *,
        prompt_name: str | None = None,
    ) -> T:
        user_content = self.render_prompt(prompt, variables)
        messages = [
            {"role": "system", "content": prompt.system.strip()},
            {"role": "user", "content": user_content},
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": prompt.name,
                "strict": True,
                "schema": prompt.output_schema,
            },
        }

        last_error: Exception | None = None
        settings = self._config.llm
        for attempt in range(settings.max_retries + 1):
            try:
                raw = await self._client.chat_completion(
                    model=settings.model,
                    messages=messages,
                    temperature=settings.temperature,
                    max_tokens=settings.max_output_tokens,
                    response_format=response_format,
                )
                self._record_usage(raw)
                content = self._extract_content(raw)
                parsed = json.loads(content)
                return result_model.model_validate(parsed)
            except (LlmClientError, json.JSONDecodeError, ValidationError, LlmAdapterError) as exc:
                last_error = exc
                self.usage.failures += 1
                logger.warning(
                    "llm structured completion failed",
                    extra={
                        "prompt": prompt_name or prompt.name,
                        "attempt": attempt + 1,
                        "error": str(exc),
                    },
                )
                if attempt < settings.max_retries:
                    await asyncio.sleep(settings.retry_backoff_seconds * (attempt + 1))

        raise LlmAdapterError(f"LLM failed after retries: {last_error}") from last_error

    def _record_usage(self, raw: dict[str, Any]) -> None:
        self.usage.requests += 1
        usage = raw.get("usage") or {}
        if isinstance(usage, dict):
            self.usage.prompt_tokens += int(usage.get("prompt_tokens") or 0)
            self.usage.completion_tokens += int(usage.get("completion_tokens") or 0)
            self.usage.total_tokens += int(usage.get("total_tokens") or 0)

    @staticmethod
    def _extract_content(raw: dict[str, Any]) -> str:
        choices = raw.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmAdapterError("LLM response missing choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise LlmAdapterError("LLM response missing message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmAdapterError("LLM response missing content")
        return content.strip()
