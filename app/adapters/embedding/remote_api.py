"""OpenAI-compatible remote embeddings provider."""

from __future__ import annotations

import logging

import httpx

from app.adapters.embedding.base import EmbeddingResult
from app.adapters.embedding.lexical import LexicalEmbeddingProvider

logger = logging.getLogger(__name__)


class RemoteApiEmbeddingProvider:
    provider_name = "remote_api"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        embedding_space: str,
        allow_lexical_fallback: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.embedding_space = embedding_space
        self._model = model
        self._allow_fallback = allow_lexical_fallback
        self._fallback = (
            LexicalEmbeddingProvider(degraded=True, reason="remote_api_unavailable")
            if allow_lexical_fallback
            else None
        )
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
        )

    async def embed(self, text: str) -> EmbeddingResult:
        try:
            response = await self._client.post(
                "/embeddings",
                json={"model": self._model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
            vector = payload["data"][0]["embedding"]
            return EmbeddingResult(
                vector=[float(x) for x in vector],
                embedding_space=self.embedding_space,
                provider=self.provider_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "remote embedding failed: %s",
                exc,
                extra={"service": "embedding", "component": "remote_api"},
            )
            if self._fallback is not None:
                result = await self._fallback.embed(text)
                return EmbeddingResult(
                    vector=result.vector,
                    embedding_space=result.embedding_space,
                    provider=result.provider,
                    degraded=True,
                    degradation_reason=f"remote_api_failed:{exc}",
                )
            raise

    async def close(self) -> None:
        await self._client.aclose()
