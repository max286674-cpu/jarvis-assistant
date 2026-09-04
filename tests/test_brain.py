"""Тесты для core/brain.py.
Не вызывают OpenRouter — проверяют только локальную логику:
- роутинг по ключевым словам
- провайдер по умолчанию
- приоритет env-переменных над config
- кэширование
- fallback при ошибке
"""
import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.brain import Brain, DEFAULT_MODELS, SYSTEM_PROMPT


@pytest.fixture
def brain_cfg():
    return {
        "provider": "openrouter",
        "max_history": 12,
        "temperature": 0.2,
        "timeout_seconds": 90,
        "max_output_tokens": 1600,
        "cache_ttl_seconds": 300,
    }


@pytest.fixture
def brain(brain_cfg):
    """Создаёт Brain с фейковым API-ключом."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake-key-for-test"}, clear=False):
        with patch("core.brain.load_dotenv"):  # не трогаем .env при тестах
            return Brain(brain_cfg, user_name="Test")


def test_default_models_exist():
    """Все 5 уровней моделей должны быть заданы по умолчанию."""
    assert "cheap" in DEFAULT_MODELS
    assert "main" in DEFAULT_MODELS
    assert "document" in DEFAULT_MODELS
    assert "hard" in DEFAULT_MODELS
    assert "max" in DEFAULT_MODELS
    assert DEFAULT_MODELS["cheap"].startswith("deepseek")
    assert DEFAULT_MODELS["max"].startswith("moonshotai")


def test_brain_disabled_without_key(brain_cfg):
    """Без API-ключа brain.enabled должен быть False."""
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.enabled is False


def test_brain_enabled_with_key(brain):
    """С ключом brain должен быть включён."""
    assert brain.enabled is True
    assert brain.provider == "openrouter"


def test_routing_short_uses_cheap(brain):
    """Короткий простой вопрос → cheap модель."""
    category, model = brain._route("привет")
    assert category == "cheap"
    assert "deepseek" in model


def test_routing_document_uses_document_model(brain):
    """Запрос с упоминанием документа → document модель."""
    category, model = brain._route("проанализируй PDF-отчёт по лабораторной")
    assert category == "document"
    assert "qwen" in model


def test_routing_hard_uses_hard_model(brain):
    """Сложный запрос (архитектура, диплом) → hard модель."""
    category, model = brain._route("спроектируй архитектуру всего проекта")
    assert category == "hard"


def test_routing_max_uses_max_model(brain):
    """Очень сложный запрос → max модель."""
    category, model = brain._route("критически важно: финальная проверка всей системы")
    assert category == "max"
    assert "kimi" in model


def test_routing_default_main(brain):
    """Обычный длинный запрос → main модель."""
    category, model = brain._route(
        "Расскажи пожалуйста подробно о преимуществах микросервисной архитектуры"
    )
    assert category == "main"
    assert "glm" in model


def test_selected_model_returns_string(brain):
    """selected_model() должен возвращать строку (имя модели)."""
    model = brain.selected_model("привет")
    assert isinstance(model, str)
    assert len(model) > 0


def test_history_limit_from_env(brain_cfg):
    """JARVIS_MAX_HISTORY должен переопределять config."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "x", "JARVIS_MAX_HISTORY": "5"}, clear=False):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.max_history == 5


def test_temperature_from_env(brain_cfg):
    """JARVIS_TEMPERATURE должен переопределять config."""
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "x", "JARVIS_TEMPERATURE": "0.7"}, clear=False):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.temperature == 0.7


def test_cache_hit(brain):
    """Кэш должен работать: повторный запрос того же текста не идёт в сеть."""
    # Наполняем кэш вручную
    key = brain._cache_key("test-model", "тестовый запрос")
    brain.cache[key] = (time.time(), "тестовый ответ")
    cached = brain._cache_get(key)
    assert cached == "тестовый ответ"


def test_cache_expiry(brain):
    """Просроченный кэш должен удаляться."""
    key = brain._cache_key("test-model", "устаревший запрос")
    # Кладём в кэш с меткой времени в прошлом
    brain.cache[key] = (time.time() - 1000, "устаревший ответ")
    brain.cache_ttl = 300
    cached = brain._cache_get(key)
    assert cached is None
    assert key not in brain.cache


def test_ask_without_enabled_returns_empty(brain_cfg):
    """ask() без ключа возвращает пустую строку."""
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("core.brain.load_dotenv"):
            b = Brain(brain_cfg, user_name="Test")
            assert b.ask("любой вопрос") == ""


def test_ask_with_empty_text_returns_empty(brain):
    """ask() с пустым текстом возвращает пустую строку."""
    assert brain.ask("") == ""
    assert brain.ask("   ") == ""


def test_ask_uses_cache_on_second_call(brain):
    """Второй вызов с тем же текстом должен попасть в кэш."""
    with patch.object(brain, "_openrouter", return_value="ответ") as mock_openrouter:
        first = brain.ask("расскажи анекдот")
        second = brain.ask("расскажи анекдот")
        assert first == "ответ"
        assert second == "ответ"
        # В сеть ходили только один раз
        assert mock_openrouter.call_count == 1


def test_ask_fallback_on_error(brain):
    """При ошибке основной модели должен сработать fallback на cheap."""
    with patch.object(brain, "_openrouter", side_effect=Exception("API down")) as mock_openrouter:
        result = brain.ask("проверка fallback")
        assert "временно недоступен" in result or "проверьте" in result
        # Ходили в сеть 2 раза: основная + fallback
        assert mock_openrouter.call_count == 2


def test_reset_memory_clears_state(brain):
    """reset_memory должен очищать и кэш, и историю."""
    brain.history.append({"role": "user", "content": "x"})
    brain.cache["key"] = (time.time(), "y")
    brain.reset_memory()
    assert len(brain.history) == 0
    assert len(brain.cache) == 0


def test_system_prompt_includes_user_name():
    """Системный промт должен подставлять имя пользователя."""
    assert "{user}" in SYSTEM_PROMPT
    prompt = SYSTEM_PROMPT.format(user="Максим")
    assert "Максим" in prompt
    assert "Джарвис" in prompt or "JARVIS" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])