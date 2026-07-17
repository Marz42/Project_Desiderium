"""Unit tests for LLM adapter prompt rendering and structured output parsing."""

from __future__ import annotations

import json

import pytest

from app.adapters.llm.adapter import LlmAdapter, LlmAdapterError
from app.adapters.llm.client import OpenAICompatibleClient
from app.schemas.semantic import TrendNamingResult
from app.services.llm_config import PromptTemplate, load_prompt_template


def test_render_prompt_substitutes_variables() -> None:
    prompt = PromptTemplate(
        version="1.0",
        name="test",
        description="",
        system="sys",
        user_template="Hello {{name}}: {{payload_json}}",
        output_schema={"type": "object"},
    )
    rendered = LlmAdapter.render_prompt(prompt, {"name": "world", "payload_json": {"a": 1}})
    assert "Hello world" in rendered
    assert '"a": 1' in rendered


def test_render_prompt_missing_variable_raises() -> None:
    prompt = PromptTemplate(
        version="1.0",
        name="test",
        description="",
        system="sys",
        user_template="{{missing}}",
        output_schema={"type": "object"},
    )
    with pytest.raises(LlmAdapterError, match="missing prompt variable"):
        LlmAdapter.render_prompt(prompt, {})


def test_extract_content_parses_openai_shape() -> None:
    raw = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {"trend_name_zh": "测试", "evidence_content_ids": ["1"], "confidence": 0.8}
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    content = LlmAdapter._extract_content(raw)
    parsed = TrendNamingResult.model_validate(json.loads(content))
    assert parsed.trend_name_zh == "测试"


def test_load_prompt_templates_exist() -> None:
    for name in (
        "title_translation",
        "trend_naming",
        "why_trending",
        "creative_angles",
        "format_classification",
    ):
        prompt = load_prompt_template(name)
        assert prompt.version
        assert prompt.output_schema.get("type") == "object"


def test_openai_client_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAICompatibleClient(api_key="")
