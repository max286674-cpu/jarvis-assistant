"""Реестр инструментов Jarvis с валидацией и защитой опасных действий."""
from __future__ import annotations
import json, re
from typing import Any, Callable

class Tool:
    def __init__(self,name:str,description:str,parameters:dict,handler:Callable[...,Any],risk:str="safe"):
        self.name=name; self.description=description; self.parameters=parameters; self.handler=handler; self.risk=risk
    def schema(self):
        return {"type":"function","function":{"name":self.name,"description":f"{self.description} Risk: {self.risk}.","parameters":self.parameters}}
    def call(self,args):
        result=self.handler(**args)
        return result if isinstance(result,str) else json.dumps(result,ensure_ascii=False,default=str)

class ToolRegistry:
    def __init__(self): self._tools={}
    def register(self,tool): self._tools[tool.name]=tool
    def schemas(self): return [t.schema() for t in self._tools.values()]
    def execute(self,name,args):
        tool=self._tools.get(name)
        if not tool: return f"Инструмент {name!r} не найден."
        # Confirm-level actions are never silently executed by an LLM.
        if tool.risk=="confirm": return f"ACTION_REQUIRES_CONFIRMATION: действие {name} требует явного подтверждения пользователя."
        try: return tool.call(args or {})
        except Exception as exc: return f"Инструмент {name} завершился с ошибкой: {exc}"
    def names(self): return list(self._tools)

def safe_url(url):
    url=(url or "").strip()
    if not re.match(r"^https?://",url,re.I): url="https://"+url
    if not re.match(r"^https?://[^\s]+$",url,re.I): raise ValueError("Некорректный URL")
    return url

def build_default_registry(executor,reminders=None,telegram=None,web_search=None):
    r=ToolRegistry()
    r.register(Tool("open_url","Открыть URL в браузере",{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]},lambda url:executor.open_url(safe_url(url))))
    r.register(Tool("open_app","Открыть Windows-приложение или локальный путь",{"type":"object","properties":{"target":{"type":"string"}},"required":["target"]},lambda target:executor.open_app(target)))
    r.register(Tool("open_folder","Открыть существующую папку",{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]},lambda path:executor.open_folder(path)))
    if reminders:
        r.register(Tool("create_reminder","Создать напоминание",{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]},lambda text:reminders.parse_and_add(text)))
        r.register(Tool("list_tasks","Показать задачи",{"type":"object","properties":{}},lambda:reminders.list_tasks()))
    if telegram:
        r.register(Tool("send_telegram","Отправить сообщение в Telegram",{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]},lambda text:telegram.send(text),"confirm"))
    if web_search:
        r.register(Tool("web_search","Найти свежую информацию в интернете",{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]},lambda query:web_search(query)))
    return r
