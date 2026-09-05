"""Cheap/agent/research model routing with deterministic rules and env overrides."""
from __future__ import annotations
import os

class ModelRouter:
    def __init__(self, models: dict[str, str]):
        self.models = models
        self.main = os.getenv("JARVIS_MODEL", models.get("main", ""))
        self.cheap = os.getenv("JARVIS_CHEAP_MODEL", models.get("cheap", self.main))
        self.research = os.getenv("JARVIS_RESEARCH_MODEL", models.get("research", self.main))

    def select(self, text: str) -> str:
        text = (text or "").lower().strip()
        research_markers = ("найди", "актуаль", "сравни", "исследуй", "источник", "последние новости", "свежие данные")
        agent_markers = ("открой", "закрой", "запусти", "файл", "папк", "браузер", "компьютер", "нажми", "напиши в", "удали")
        trivial_markers = ("привет", "спасибо", "понятно", "хорошо", "да", "нет", "который час", "сколько времени")
        if any(x in text for x in research_markers): return self.research or self.main
        if any(x in text for x in agent_markers): return self.main
        if len(text) < 45 and any(x in text for x in trivial_markers): return self.cheap or self.main
        return self.main
