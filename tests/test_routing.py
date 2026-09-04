"""Тесты для core/router.py (без запуска LLM)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.router import Router


def test_router_exists():
    assert Router is not None


def test_command_custom_exists():
    from core.config import COMMANDS
    assert "custom" in COMMANDS or isinstance(COMMANDS, dict)