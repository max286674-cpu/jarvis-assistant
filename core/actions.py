"""Исполнитель действий: открытие программ, папок, ссылок, команды ОС (Windows)."""
import os
import subprocess
import webbrowser


class ActionExecutor:
    def __init__(self, speaker):
        self.speaker = speaker

    def run(self, action: dict) -> str:
        atype = action.get("type", "")
        target = action.get("target", "")
        try:
            if atype == "open_app":
                return self.open_app(target)
            if atype == "open_folder":
                return self.open_folder(target)
            if atype == "open_url":
                return self.open_url(target)
            if atype == "run_cmd":
                subprocess.Popen(target, shell=True)
                return f"Выполняю команду."
            if atype == "say":
                self.speaker.say(target)
                return target
            return f"Неизвестный тип действия: {atype}"
        except Exception as e:
            return f"Не получилось: {e}"

    @staticmethod
    def open_app(path_or_name: str) -> str:
        if not path_or_name:
            return "Путь к программе не указан в commands.json"
        name = os.path.basename(path_or_name).lower()
        known = {
            "code": ["code"], "chrome": ["chrome"],
            "explorer": ["explorer"], "notepad": ["notepad"],
            "terminal": ["wt", "cmd"], "spotify": ["spotify"],
        }
        cmds = known.get(name.replace(".exe", ""))
        if not os.path.exists(path_or_name) and cmds:
            for c in cmds:
                try:
                    subprocess.Popen([c], shell=True)
                    return f"Открываю {name}."
                except Exception:
                    continue
        subprocess.Popen(["cmd", "/c", "start", "", path_or_name], shell=True)
        return f"Запускаю {os.path.basename(path_or_name)}."

    @staticmethod
    def open_folder(path: str) -> str:
        if not path or not os.path.isdir(path):
            return f"Папка не найдена: {path}"
        subprocess.Popen(["explorer", path])
        return f"Открываю папку."

    @staticmethod
    def open_url(url: str) -> str:
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return "Открываю браузер."

    @staticmethod
    def screenshot(path: str = None) -> str:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            save_path = path or os.path.expanduser("~/Pictures/jarvis_screenshot.png")
            img.save(save_path)
            return f"Скриншот сохранён: {save_path}"
        except Exception as e:
            return f"Не удалось сделать скриншот: {e}"

    @staticmethod
    def open_browser(url: str = "https://google.com") -> str:
        webbrowser.open(url)
        return f"Открываю браузер: {url}"

    @staticmethod
    def run_system_command(cmd: str) -> str:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.stdout[:500] if result.stdout else "Команда выполнена."
        except Exception as e:
            return f"Ошибка выполнения: {e}"
