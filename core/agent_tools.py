"""Безопасный реестр инструментов Jarvis."""
from __future__ import annotations
import json
import re
from typing import Any, Callable

class Tool:
    def __init__(self, name: str, description: str, parameters: dict, handler: Callable[..., Any], risk: str = "safe"):
        self.name, self.description, self.parameters, self.handler, self.risk = name, description, parameters, handler, risk
    def schema(self) -> dict:
        return {"type":"function","function":{"name":self.name,"description":f"{self.description} Risk: {self.risk}.","parameters":self.parameters}}
    def call(self, args: dict) -> str:
        result = self.handler(**args)
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)

class ToolRegistry:
    def __init__(self): self._tools: dict[str, Tool] = {}
    def register(self, tool: Tool) -> None: self._tools[tool.name] = tool
    def schemas(self) -> list[dict]: return [t.schema() for t in self._tools.values()]
    def execute(self, name: str, args: dict) -> str:
        tool = self._tools.get(name)
        if not tool: return f"Инструмент {name!r} не найден."
        try: return tool.call(args)
        except Exception as exc: return f"Инструмент {name} завершился с ошибкой: {exc}"
    def names(self) -> list[str]: return list(self._tools)

def safe_url(url: str) -> str:
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I): url = "https://" + url
    if not re.match(r"^https?://[^\s]+$", url, re.I): raise ValueError("Некорректный URL")
    return url

def build_default_registry(executor, reminders=None, telegram=None, web_search=None) -> ToolRegistry:
    r = ToolRegistry()
    r.register(Tool("open_url","Открыть URL в браузере",{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]},lambda url: executor.open_url(safe_url(url))))
    r.register(Tool("open_app","Открыть Windows-приложение или локальный путь",{"type":"object","properties":{"target":{"type":"string"}},"required":["target"]},lambda target: executor.open_app(target)))
    r.register(Tool("open_folder","Открыть существующую папку",{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]},lambda path: executor.open_folder(path)))
    if reminders:
        r.register(Tool("create_reminder","Создать напоминание из естественной фразы",{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]},lambda text: reminders.parse_and_add(text)))
        r.register(Tool("list_tasks","Показать текущие задачи",{"type":"object","properties":{}},lambda: reminders.list_tasks()))
    if telegram:
        r.register(Tool("send_telegram","Отправить сообщение в Telegram",{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]},lambda text: telegram.send(text),"confirm"))
    if web_search:
        r.register(Tool("web_search","Найти свежую информацию в интернете",{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},lambda query: web_search(query)))
    return r
