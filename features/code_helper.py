"""Помощник по коду: читает ошибку из буфера обмена или файла, объясняет через Gemini."""
import subprocess


class CodeHelper:
    def __init__(self, brain):
        self.brain = brain

    @staticmethod
    def get_clipboard() -> str:
        try:
            out = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="ignore",
            )
            return out.stdout.strip()
        except Exception:
            return ""

    def explain_error(self) -> str:
        """«Джарвис, что не так?» — берёт текст ошибки из буфера обмена."""
        clip = self.get_clipboard()
        if not clip or len(clip) < 5:
            return ("Сэр, буфер обмена пуст. Скопируйте текст ошибки "
                    "(Ctrl+C на сообщении) и спросите снова.")
        prompt = (
            "Разбери эту ошибку программиста. Ответь по-русски кратко: "
            "1) что сломалось, 2) самая вероятная причина, "
            "3) конкретное исправление (код, если нужен). Текст ошибки:\n\n"
            f"{clip[:4000]}"
        )
        answer = self.brain.ask(prompt)
        return answer or "Мозг недоступен, но ошибка точно чья-то. Не моя."

    def explain_code(self, path: str) -> str:
        """«Джарвис, объясни файл ...» — читает файл и разбирает."""
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                code = f.read(8000)
        except Exception as e:
            return f"Не смог прочитать файл: {e}"
        prompt = (
            "Объясни по-русски кратко, что делает этот код: структура, "
            "назначение, подозрительные места.\n\n"
            f"{code}"
        )
        return self.brain.ask(prompt) or "Мозг занят размышлениями о смысле кода."

    def find_bugs(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                code = f.read(8000)
        except Exception as e:
            return f"Не смог прочитать файл: {e}"
        prompt = (
            "Найди баги и проблемы в этом коде. Перечисли кратко списком: "
            "строка/место → проблема → исправление.\n\n"
            f"{code}"
        )
        return self.brain.ask(prompt) or "Код настолько хорош, что я в шоке. Или мозг отключён."
