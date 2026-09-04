"""Full-duplex TTS: озвучка не блокирует микрофон и может быть прервана."""
from __future__ import annotations

import asyncio
import os
import tempfile
import threading

import edge_tts


class DuplexSpeaker:
    def __init__(self, voice_cfg: dict):
        self.cfg = voice_cfg
        self._stop = threading.Event()
        self._speaking = threading.Event()
        self._thread = None

    @property
    def speaking(self):
        return self._speaking.is_set()

    def stop(self):
        self._stop.set()
        try:
            import pygame
            pygame.mixer.music.stop()
        except Exception:
            pass

    def say(self, text: str, blocking: bool = True):
        text = (text or "").strip()
        if not text:
            return
        self.stop()
        self._stop.clear()
        if blocking:
            self._speak(text)
        else:
            self._thread = threading.Thread(target=self._speak, args=(text,), daemon=True)
            self._thread.start()

    def _speak(self, text):
        print(f"🤖 Джарвис: {text}")
        self._speaking.set()
        try:
            asyncio.run(self._play_edge(text))
        except Exception as exc:
            if not self._stop.is_set():
                print(f"[TTS error: {exc}]")
                self._offline(text)
        finally:
            self._speaking.clear()
            self._stop.clear()

    async def _play_edge(self, text):
        import pygame
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        try:
            await edge_tts.Communicate(
                text,
                self.cfg.get("tts_voice", "ru-RU-DmitryNeural"),
                rate=self.cfg.get("rate", "+0%"),
            ).save(tmp.name)
            if self._stop.is_set():
                return
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(tmp.name)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop.is_set():
                await asyncio.sleep(0.05)
            pygame.mixer.music.stop()
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def _offline(self, text):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 180)
            for voice in engine.getProperty("voices"):
                if "ru" in f"{voice.id} {voice.name}".lower():
                    engine.setProperty("voice", voice.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception as exc:
            print(f"[TTS недоступен: {exc}]")
