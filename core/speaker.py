"""Голос Джарвиса: edge-tts (онлайн, красивый русский голос) + pyttsx3 (офлайн-фолбэк)."""
import asyncio
import threading

import edge_tts


class Speaker:
    def __init__(self, voice_cfg: dict):
        self.cfg = voice_cfg
        self._lock = threading.Lock()

    def say(self, text: str) -> None:
        print(f"🤖 Джарвис: {text}")
        with self._lock:
            try:
                asyncio.run(self._edge(text))
            except Exception:
                self._offline(text)

    async def _edge(self, text: str) -> None:
        import playsound3, tempfile, os
        # Всегда используем мужской голос, без дублирования
        voice = "en-US-GuyNeural"
        rate = self.cfg.get("rate", "+20%")
        tts = edge_tts.Communicate(text, voice, rate=rate)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        await tts.save(tmp.name)
        try:
            playsound3.playsound(tmp.name)
        finally:
            os.unlink(tmp.name)

    def _offline(self, text: str) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 180)
            for v in engine.getProperty("voices"):
                if "ru" in (v.id + v.name).lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS недоступен: {e}]")
