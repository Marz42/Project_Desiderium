"""Record and summarize LLM token usage."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.repositories.ops import OpsRepository


def estimate_llm_cost_usd(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    settings: Settings | None = None,
) -> float:
    settings = settings or get_settings()
    input_cost = (prompt_tokens / 1_000_000) * settings.llm_cost_per_million_input_usd
    output_cost = (completion_tokens / 1_000_000) * settings.llm_cost_per_million_output_usd
    return round(input_cost + output_cost, 6)


async def record_llm_call(
    session: AsyncSession,
    *,
    job_name: str,
    prompt_name: str | None,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    cost = estimate_llm_cost_usd(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        settings=settings,
    )
    repo = OpsRepository(session)
    await repo.record_llm_usage(
        job_name=job_name,
        prompt_name=prompt_name,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd_estimate=cost,
    )
