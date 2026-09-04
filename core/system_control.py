"""Полный контроль компьютера для Jarvis.
Управление файлами, приложениями, браузером, громкостью, экраном, процессами."""
import os
import subprocess
import webbrowser
import time


class SystemControl:
    """Полный доступ к системе Windows."""

    @staticmethod
    def list_files(path: str = ".") -> str:
        try:
            files = os.listdir(path)
            return f"Файлы в {path}: {', '.join(files[:20])}"
        except Exception as e:
            return f"Ошибка: {e}"

    @staticmethod
    def read_file(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()[:2000]
        except Exception as e:
            return f"Не могу прочитать: {e}"

    @staticmethod
    def write_file(path: str, content: str) -> str:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Записал в {path}"
        except Exception as e:
            return f"Ошибка записи: {e}"

    @staticmethod
    def delete_file(path: str) -> str:
        try:
            os.remove(path)
            return f"Удалил {path}"
        except Exception as e:
            return f"Ошибка удаления: {e}"

    @staticmethod
    def open_app(name: str) -> str:
        apps = {
            "chrome": "chrome", "firefox": "firefox", "edge": "msedge",
            "vscode": "code", "notepad": "notepad", "word": "winword",
            "excel": "excel", "powerpoint": "powerpnt", "explorer": "explorer",
            "terminal": "wt", "cmd": "cmd", "spotify": "spotify",
        }
        cmd = apps.get(name.lower(), name)
        try:
            subprocess.Popen([cmd], shell=True)
            return f"Открываю {name}"
        except Exception as e:
            return f"Не открыл: {e}"

    @staticmethod
    def open_folder(path: str) -> str:
        try:
            subprocess.Popen(["explorer", path])
            return f"Открываю папку {path}"
        except Exception as e:
            return f"Ошибка: {e}"

    @staticmethod
    def open_url(url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Открываю {url}"

    @staticmethod
    def screenshot(path: str = None) -> str:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            save_path = path or os.path.expanduser("~/Pictures/jarvis_screenshot.png")
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            img.save(save_path)
            return f"Скриншот: {save_path}"
        except Exception as e:
            return f"Ошибка скриншота: {e}"

    @staticmethod
    def volume_up() -> str:
        try:
            subprocess.run(["nircmd", "changesysvolume", "2000"], capture_output=True)
            return "Громкость увеличена"
        except:
            return "Громкость + (nircmd не установлен)"

    @staticmethod
    def volume_down() -> str:
        try:
            subprocess.run(["nircmd", "changesysvolume", "-2000"], capture_output=True)
            return "Громкость уменьшена"
        except:
            return "Громкость -"

    @staticmethod
    def volume_mute() -> str:
        try:
            subprocess.run(["nircmd", "mutesysvolume", "2"], capture_output=True)
            return "Звук выключен"
        except:
            return "Мут (nircmd не установлен)"

    @staticmethod
    def run_command(cmd: str) -> str:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            out = result.stdout[:1000] if result.stdout else "Выполнено"
            return f"Результат: {out}"
        except Exception as e:
            return f"Ошибка команды: {e}"

    @staticmethod
    def kill_process(name: str) -> str:
        try:
            subprocess.run(f"taskkill /F /IM {name}", shell=True, capture_output=True)
            return f"Завершил процесс {name}"
        except Exception as e:
            return f"Не удалось: {e}"

    @staticmethod
    def list_processes() -> str:
        try:
            result = subprocess.run("tasklist /FI \"STATUS eq RUNNING\"", shell=True, capture_output=True, text=True)
            lines = result.stdout.split("\n")[:10]
            return "Процессы: " + ", ".join(lines)
        except Exception as e:
            return f"Ошибка: {e}"

    @staticmethod
    def get_system_info() -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            return f"CPU: {cpu}%, RAM: {mem.percent}%, Диск: {mem.used//1024//1024}MB"
        except Exception as e:
            return f"Информация о системе: {e}"