"""Tests for LLM cost estimation."""

import pytest

from app.services.llm_usage import estimate_llm_cost_usd


def test_estimate_llm_cost_usd():
    cost = estimate_llm_cost_usd(prompt_tokens=1_000_000, completion_tokens=500_000)
    # default rates: 0.15 input + 0.30 output = 0.45
    assert cost == pytest.approx(0.45, rel=1e-3)
