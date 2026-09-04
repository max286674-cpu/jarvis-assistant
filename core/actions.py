"""Безопасный исполнитель локальных действий Windows."""
import os
import subprocess
import webbrowser

class ActionExecutor:
    def __init__(self, speaker): self.speaker = speaker

    def run(self, action: dict) -> str:
        atype, target = action.get("type", ""), action.get("target", "")
        try:
            if atype == "open_app": return self.open_app(target)
            if atype == "open_folder": return self.open_folder(target)
            if atype == "open_url": return self.open_url(target)
            if atype == "say":
                self.speaker.say(target); return target
            if atype == "run_cmd":
                return "Выполнение произвольных shell-команд отключено из соображений безопасности."
            return f"Неизвестный тип действия: {atype}"
        except Exception as e: return f"Не получилось выполнить действие: {e}"

    @staticmethod
    def open_app(path_or_name: str) -> str:
        if not path_or_name: return "Путь к программе не указан."
        name = os.path.basename(path_or_name).lower().replace(".exe", "")
        known = {"code":"code", "chrome":"chrome", "explorer":"explorer", "notepad":"notepad", "terminal":"wt", "spotify":"spotify"}
        if name in known:
            subprocess.Popen([known[name]], shell=False)
            return f"Открываю {name}."
        if os.path.isfile(path_or_name) and path_or_name.lower().endswith(".exe"):
            subprocess.Popen([path_or_name], shell=False); return f"Запускаю {os.path.basename(path_or_name)}."
        return f"Неизвестное приложение: {path_or_name}. Добавьте его в разрешённый список."

    @staticmethod
    def open_folder(path: str) -> str:
        if not path or not os.path.isdir(path): return f"Папка не найдена: {path}"
        subprocess.Popen(["explorer", os.path.abspath(path)], shell=False); return "Открываю папку."

    @staticmethod
    def open_url(url: str) -> str:
        if not url: return "URL не указан."
        if not url.startswith(("http://", "https://")): url = "https://" + url
        webbrowser.open(url); return "Открываю браузер."
