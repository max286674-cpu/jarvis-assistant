"""Помощник по коду: безопасно читает ошибки и файлы из Workspace."""
import subprocess

class CodeHelper:
    def __init__(self, brain, workspace=None):
        self.brain = brain
        self.workspace = workspace

    @staticmethod
    def get_clipboard() -> str:
        try:
            out = subprocess.run(["powershell", "-command", "Get-Clipboard"], capture_output=True, text=True, timeout=10, encoding="utf-8", errors="ignore")
            return out.stdout.strip()[:12000]
        except Exception:
            return ""

    def explain_error(self) -> str:
        clip = self.get_clipboard()
        if not clip or len(clip) < 5:
            return "Сэр, буфер обмена пуст. Скопируйте текст ошибки и спросите снова."
        answer = self.brain.ask("Разбери ошибку программиста по-русски: что сломалось, вероятная причина и конкретное исправление. Ошибка:\n\n" + clip[:4000])
        return answer or "Мозг недоступен."

    def _read(self, path: str) -> str:
        if self.workspace:
            return self.workspace.read_text(path)[:12000]
        raise PermissionError("Рабочая область не настроена.")

    def explain_code(self, path: str) -> str:
        try: code = self._read(path)
        except Exception as e: return f"Не смог прочитать файл: {e}"
        answer = self.brain.ask("Объясни по-русски кратко этот код: структура, назначение, подозрительные места.\n\n" + code)
        return answer or "Мозг недоступен."

    def find_bugs(self, path: str) -> str:
        try: code = self._read(path)
        except Exception as e: return f"Не смог прочитать файл: {e}"
        answer = self.brain.ask("Найди баги и проблемы в этом коде. Формат: место → проблема → исправление.\n\n" + code)
        return answer or "Мозг недоступен."
