"""Голос Джарвиса: edge-tts (онлайн) + pyttsx3 (офлайн) с возможностью остановки."""
import asyncio
import threading
import edge_tts


class Speaker:
    def __init__(self, voice_cfg: dict):
        self.cfg = voice_cfg
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._current_engine = None

    def say(self, text: str) -> None:
        print(f"🤖 Джарвис: {text}")
        with self._lock:
            self._stop_requested.clear()
            try:
                asyncio.run(self._edge(text))
            except Exception:
                self._offline(text)

    async def _edge(self, text: str) -> None:
        import playsound3, tempfile, os
        voice = "ru-RU-DmitryNeural"
        rate = self.cfg.get("rate", "+20%")
        tts = edge_tts.Communicate(text, voice, rate=rate)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        await tts.save(tmp.name)
        try:
            playsound3.playsound(tmp.name)
        finally:
            os.unlink(tmp.name)

    def stop(self) -> None:
        """Останавливает текущую речь."""
        self._stop_requested.set()
        if self._current_engine:
            try:
                self._current_engine.stop()
            except Exception:
                pass

    def screenshot(self, path: str = None) -> str:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            save_path = path or os.path.expanduser("~/Pictures/jarvis_screenshot.png")
            img.save(save_path)
            return f"Скриншот сохранён: {save_path}"
        except Exception as e:
            return f"Не удалось сделать скриншот: {e}"

    def open_browser(self, url: str = "https://google.com") -> str:
        import webbrowser
        webbrowser.open(url)
        return f"Открываю браузер: {url}"

    def _offline(self, text: str) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            self._current_engine = engine
            engine.setProperty("rate", 180)
            for v in engine.getProperty("voices"):
                if "ru" in (v.id + v.name).lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS недоступен: {e}]")
        finally:
            self._current_engine = None
