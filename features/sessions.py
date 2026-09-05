"""Сессии работы: сохранение и восстановление рабочей среды."""
import json
import time

from core.config import data_file

SESSION_FILE = "session.json"

class SessionManager:
    def __init__(self, speaker):
        self.speaker = speaker
        self.path = data_file(SESSION_FILE)
        self.current = {"apps": [], "folders": [], "urls": [], "saved_at": 0}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.current, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _load(self):
        if not self.path.exists(): return None
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): return None

    def save_current(self) -> str:
        try:
            import psutil
            excluded = {"svchost.exe","runtimebroker.exe","csrss.exe","winlogon.exe","services.exe","smss.exe","lsass.exe","system.exe","explorer.exe","python.exe","pythonw.exe","conhost.exe","dllhost.exe"}
            apps = set()
            for p in psutil.process_iter(["name"]):
                try: name = (p.info.get("name") or "").lower()
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
                if name.endswith(".exe") and name not in excluded: apps.add(name)
            self.current["apps"] = sorted(apps)[:20]
            self.current["saved_at"] = time.time()
            self._save()
            return f"Сессия сохранена: {len(self.current['apps'])} программ."
        except Exception as e: return f"Не смог сохранить сессию: {e}"

    def restore(self, executor) -> str:
        session = self._load()
        if not session: return "Сэр, архив сессий пуст или повреждён. Сначала скажите «сохрани сессию»."
        opened = failed = 0
        for app in session.get("apps", [])[:20]:
            try:
                res = executor.open_app(app)
                if "Запускаю" in res or "Открываю" in res: opened += 1
                else: failed += 1
            except Exception: failed += 1
        suffix = f", не найдено: {failed}" if failed else ""
        return f"Восстанавливаю рабочую обстановку: запущено {opened} программ{suffix}."

    def add_to_session(self, kind: str, target: str) -> None:
        if kind not in ("apps", "folders", "urls") or not target: return
        if target not in self.current.get(kind, []):
            self.current.setdefault(kind, []).append(target)
            self.current["saved_at"] = time.time()
            self._save()
