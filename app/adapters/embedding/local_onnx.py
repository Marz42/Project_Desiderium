"""Local Sentence Transformers / ONNX embedding provider with lexical fallback."""

from __future__ import annotations

import logging

from app.adapters.embedding.base import EmbeddingResult
from app.adapters.embedding.lexical import LexicalEmbeddingProvider

logger = logging.getLogger(__name__)


class LocalOnnxEmbeddingProvider:
    provider_name = "local_onnx"

    def __init__(
        self,
        *,
        model_name: str,
        model_revision: str,
        embedding_space: str,
        allow_lexical_fallback: bool = True,
    ) -> None:
        self.embedding_space = embedding_space
        self._model_name = model_name
        self._model_revision = model_revision
        self._allow_fallback = allow_lexical_fallback
        self._model = None
        self._fallback: LexicalEmbeddingProvider | None = None
        self._load_error: str | None = None
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

            self._model = SentenceTransformer(
                model_name,
                revision=model_revision,
            )
        except Exception as exc:  # noqa: BLE001
            self._load_error = str(exc)
            logger.warning(
                "local onnx embedding unavailable: %s",
                exc,
                extra={"service": "embedding", "component": "local_onnx"},
            )
            if allow_lexical_fallback:
                self._fallback = LexicalEmbeddingProvider(
                    degraded=True,
                    reason=f"local_onnx_unavailable:{exc}",
                )

    async def embed(self, text: str) -> EmbeddingResult:
        if self._model is not None:
            vector = self._model.encode(text, normalize_embeddings=True)
            return EmbeddingResult(
                vector=[float(x) for x in vector],
                embedding_space=self.embedding_space,
                provider=self.provider_name,
            )
        if self._fallback is not None:
            return await self._fallback.embed(text)
        raise RuntimeError(self._load_error or "local onnx embedding unavailable")

    async def close(self) -> None:
        self._model = None
