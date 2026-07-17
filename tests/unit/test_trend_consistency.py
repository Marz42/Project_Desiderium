from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.embedding.base import EmbeddingResult
from app.adapters.llm.adapter import LlmAdapterError
from app.models import ClusterDecisionAction, ClusterDecisionSource, TopicType, TrendTheme
from app.services.scoring_config import get_scoring_config
from app.services.trend_consistency import TrendConsistencyService


class _Embedding:
    provider_name = "test"

    def __init__(self, result: EmbeddingResult) -> None:
        self.embedding_space = result.embedding_space
        self._result = result

    async def embed(self, text: str) -> EmbeddingResult:
        return self._result

    async def close(self) -> None:
        return None


class _FailingLlm:
    async def complete_structured(self, *args, **kwargs):
        raise LlmAdapterError("timeout")


@pytest.mark.asyncio
async def test_embedding_space_mismatch_is_rejected() -> None:
    config = get_scoring_config().clustering
    embedding = _Embedding(
        EmbeddingResult(
            vector=[1.0, 0.0],
            embedding_space="remote:other-model",
            provider="remote_api",
        ),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    service = TrendConsistencyService(session, embedding=embedding, config=config)

    with pytest.raises(RuntimeError, match="embedding space mismatch"):
        await service.decide_target_trend(
            source_cluster_key="entity",
            source_meta={"anime_title": "Anime"},
            members=[{"title": "Title"}],
        )


@pytest.mark.asyncio
async def test_lexical_degradation_does_not_apply_embedding_thresholds() -> None:
    config = get_scoring_config().clustering
    embedding = _Embedding(
        EmbeddingResult(
            vector=[1.0, 0.0],
            embedding_space="lexical:char-ngram-v1",
            provider="lexical",
            degraded=True,
            degradation_reason="onnx unavailable",
        ),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    service = TrendConsistencyService(session, embedding=embedding, config=config)

    decision = await service.decide_target_trend(
        source_cluster_key="entity",
        source_meta={"anime_title": "Anime"},
        members=[{"title": "Title"}],
    )

    assert decision.action == ClusterDecisionAction.CREATE_NEW_THEME
    assert decision.source == ClusterDecisionSource.LEXICAL
    assert decision.similarity is None
    assert decision.degraded is True


@pytest.mark.asyncio
async def test_llm_timeout_returns_conservative_needs_review() -> None:
    config = get_scoring_config().clustering
    embedding = _Embedding(
        EmbeddingResult(
            vector=[1.0, 0.0],
            embedding_space=config.embedding.embedding_space,
            provider="local_onnx",
        ),
    )
    session = AsyncMock(spec=AsyncSession)
    service = TrendConsistencyService(
        session,
        embedding=embedding,
        llm=_FailingLlm(),  # type: ignore[arg-type]
        config=config,
    )
    candidate = TrendTheme(
        id=uuid.uuid4(),
        canonical_name="Candidate",
        topic_type=TopicType.ANIME,
        first_detected_at=datetime.now(UTC),
        last_active_at=datetime.now(UTC),
    )

    decision = await service._adjudicate_gray_zone(
        source_meta={"anime_title": "Anime"},
        members=[{"title": "Title"}],
        candidate=candidate,
        candidate_payload={},
        similarity=0.8,
        embedding_space=config.embedding.embedding_space,
        degraded=False,
    )

    assert decision.action == ClusterDecisionAction.NEEDS_REVIEW
    assert decision.confidence is None
    assert decision.reason.startswith("llm_failed:")
