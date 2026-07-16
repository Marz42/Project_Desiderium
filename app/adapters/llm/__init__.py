"""Provider-agnostic LLM adapter (OpenAI-compatible API)."""

from app.adapters.llm.adapter import LlmAdapter, LlmAdapterError
from app.adapters.llm.client import OpenAICompatibleClient

__all__ = ["LlmAdapter", "LlmAdapterError", "OpenAICompatibleClient"]
