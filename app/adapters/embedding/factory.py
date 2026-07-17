"""Build embedding providers from scoring config."""

from __future__ import annotations

from app.adapters.embedding.base import EmbeddingProvider
from app.adapters.embedding.lexical import LexicalEmbeddingProvider
from app.adapters.embedding.local_onnx import LocalOnnxEmbeddingProvider
from app.adapters.embedding.remote_api import RemoteApiEmbeddingProvider
from app.config import get_settings
from app.services.scoring_config import ClusteringConfig, get_scoring_config


def create_embedding_provider(
    clustering: ClusteringConfig | None = None,
) -> EmbeddingProvider:
    cfg = clustering or get_scoring_config().clustering
    emb = cfg.embedding
    if emb.provider == "lexical":
        return LexicalEmbeddingProvider()
    if emb.provider == "remote_api":
        settings = get_settings()
        return RemoteApiEmbeddingProvider(
            base_url=emb.remote_base_url or settings.llm_base_url or "",
            api_key=settings.llm_api_key or "",
            model=emb.remote_model or emb.model_name,
            embedding_space=emb.embedding_space,
            allow_lexical_fallback=emb.allow_lexical_fallback,
        )
    if emb.provider == "local_onnx":
        return LocalOnnxEmbeddingProvider(
            model_name=emb.model_name,
            model_revision=emb.model_revision,
            embedding_space=emb.embedding_space,
            allow_lexical_fallback=emb.allow_lexical_fallback,
        )
    raise ValueError(f"unsupported embedding provider: {emb.provider}")
