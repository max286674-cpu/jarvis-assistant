"""Локальные тесты Brain без обращения к реальному OpenRouter."""
import os
import time
from unittest.mock import patch

import pytest

from core.brain import Brain, SYSTEM_PROMPT


@pytest.fixture
def brain_cfg():
    return {
        "provider": "openrouter",
        "model": "z-ai/glm-5.3-flash",
        "models": {
            "main": "z-ai/glm-5.3-flash",
            "cheap": "deepseek/deepseek-v4-flash-0731",
        },
        "max_history": 12,
        "temperature": 0.2,
        "timeout_seconds": 90,
        "max_output_tokens": 1600,
        "cache_ttl_seconds": 300,
    }


@pytest.fixture
def brain(brain_cfg):
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-key-for-test"}, clear=False):
        with patch("core.brain.load_dotenv"):
            return Brain(brain_cfg, user_name="Test")


def test_brain_disabled_without_key(brain_cfg):
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("core.brain.load_dotenv"):
            assert Brain(brain_cfg, user_name="Test").enabled is False


def test_brain_enabled_with_key(brain):
    assert brain.enabled is True
    assert brain.provider == "openrouter"
    assert brain.selected_model("привет") == "z-ai/glm-5.3-flash"


def test_env_overrides_config(brain_cfg):
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "x",
        "JARVIS_MODEL": "test/main",
        "JARVIS_MAX_HISTORY": "5",
        "JARVIS_TEMPERATURE": "0.7",
    }, clear=False):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.models["main"] == "test/main"
            assert b.max_history == 5
            assert b.temperature == 0.7


def test_cache_hit_and_expiry(brain):
    key = brain._cache_key("test-model", "тест")
    brain.cache[key] = (time.time(), "ответ")
    assert brain._cache_get(key) == "ответ"
    brain.cache[key] = (time.time() - 1000, "старый ответ")
    assert brain._cache_get(key) is None
    assert key not in brain.cache


def test_cache_disabled_by_zero_ttl(brain):
    brain.cache_ttl = 0
    key = brain._cache_key("test-model", "тест")
    brain.cache[key] = (time.time(), "ответ")
    assert brain._cache_get(key) is None


def test_ask_empty_or_disabled(brain_cfg):
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.ask("любой вопрос") == ""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "x"}, clear=False):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.ask("") == ""


def test_ask_fallback_on_error(brain):
    with patch.object(brain, "_openrouter", side_effect=Exception("API down")) as call:
        result = brain.ask("проверка fallback")
        assert "AI-модуль" in result or "проверьте" in result.lower()
        assert call.call_count == 2


def test_reset_memory_clears_state(brain):
    brain.history.append({"role": "user", "content": "x"})
    brain.cache["key"] = (time.time(), "y")
    brain.reset_memory()
    assert len(brain.history) == 0
    assert len(brain.cache) == 0


def test_system_prompt_is_russian_and_has_user_placeholder():
    assert "{user}" in SYSTEM_PROMPT
    prompt = SYSTEM_PROMPT.format(user="Максим")
    assert "Максим" in prompt
    assert "ТОЛЬКО НА РУССКОМ" in prompt


def test_tool_loop_executes_multiple_tools(brain):
    class FakeTools:
        def schemas(self):
            return [{"type": "function", "function": {"name": "ping", "parameters": {"type": "object"}}}]
        def execute(self, name, args):
            return f"result:{name}:{args.get('x')}"

    brain.tools = FakeTools()
    responses = [
        {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "1", "function": {"name": "ping", "arguments": '{"x": 7}'}},
            {"id": "2", "function": {"name": "ping", "arguments": '{"x": 8}'}},
        ]}}]},
        {"choices": [{"message": {"role": "assistant", "content": "Готово."}}]},
    ]
    with patch.object(brain, "_request", side_effect=responses):
        assert brain._openrouter("проверка", "test-model") == "Готово."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
