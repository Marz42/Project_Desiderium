"""Embedding providers for bounded trend recall."""

from app.adapters.embedding.base import EmbeddingProvider, EmbeddingResult
from app.adapters.embedding.factory import create_embedding_provider

__all__ = ["EmbeddingProvider", "EmbeddingResult", "create_embedding_provider"]
