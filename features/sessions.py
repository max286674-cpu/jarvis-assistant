"""Сессии работы: сохранение и восстановление «где я остановился»."""
import json
import time

from core.config import data_file, save_json

SESSION_FILE = "session.json"


class SessionManager:
    def __init__(self, speaker):
        self.speaker = speaker
        self.current = {"apps": [], "folders": [], "urls": [], "saved_at": 0}

    def save_current(self) -> str:
        """Сохраняет текущий набор открытых окон Windows как сессию."""
        try:
            import psutil
            apps = set()
            for p in psutil.process_iter(["name"]):
                n = (p.info["name"] or "").lower()
                if n.endswith(".exe") and not any(
                    x in n for x in ("svchost", "runtime", "csrss", "winlogon",
                                     "services", "smss", "lsass", "system",
                                     "explorer", "python", "conhost", "dllhost")
                ):
                    apps.add(n)
            self.current["apps"] = sorted(apps)[:15]
            self.current["saved_at"] = time.time()
            save_json(SESSION_FILE, self.current)
            return f"Сессия сохранена: {len(self.current['apps'])} программ."
        except Exception as e:
            return f"Не смог сохранить сессию: {e}"

    def restore(self, executor) -> str:
        """Открывает всё из сохранённой сессии."""
        path = data_file(SESSION_FILE)
        if not path.exists():
            return "Сэр, архив сессий пуст. Сначала скажите «сохрани сессию»."
        with open(path, encoding="utf-8") as f:
            session = json.load(f)
        opened = 0
        for app in session.get("apps", []):
            res = executor.open_app(app)
            if "Запускаю" in res or "Открываю" in res:
                opened += 1
        return f"Восстанавливаю рабочую обстановку: запущено {opened} программ."

    def add_to_session(self, kind: str, target: str) -> None:
        if target and target not in self.current.get(kind, []):
            self.current.setdefault(kind, []).append(target)
            save_json(SESSION_FILE, self.current)
