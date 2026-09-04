"""Тонкий входной слой: бизнес-решения принимает AI-агент, а не гигантский набор regex."""
from core.config import CONFIG, COMMANDS
class Router:
    def __init__(self,speaker,executor,sessions,reminders,brain,code_helper,telegram=None):
        self.speaker=speaker;self.executor=executor;self.sessions=sessions;self.reminders=reminders;self.brain=brain;self.code_helper=code_helper;self.telegram=telegram;self.crypto_watch=None;self.tenders=None
    def attach(self,crypto_watch=None,tenders=None):self.crypto_watch=crypto_watch;self.tenders=tenders
    def _legacy_command(self,text):
        low=text.lower().strip();session=CONFIG.get("session",{})
        if any(w.lower() in low for w in session.get("restore_command",[])):return self.sessions.restore(self.executor)+" Рабочий режим активирован, сэр."
        if any(w.lower() in low for w in session.get("rest_command",[])):
            for action in COMMANDS.get("rest_mode",{}).get("actions",[]):self.executor.run(action)
            return "Отдыхаем, сэр."
        if "сохрани сессию" in low or "сохранить сессию" in low:return self.sessions.save_current()
        if low in ("тишина","молчи","стоп","замолчи"):return "..."
        if low in ("сбрось память","очисти память","забудь диалог"):self.brain.reset_memory();return "Контекст текущего диалога очищен, сэр."
        if low in ("удали всю память","очисти всю память"):self.brain.clear_persistent_memory();return "Постоянная память очищена, сэр."
        return None
    def handle(self,text):
        text=(text or "").strip()
        if not text:return ""
        direct=self._legacy_command(text)
        if direct is not None:return direct
        answer=self.brain.ask(text)
        return answer or "Сэр, AI-модуль не подключён. Проверьте OPENROUTER_API_KEY и JARVIS_MODEL."
