"""Слух Джарвиса: микрофон → текст (Google Web Speech, бесплатно, без ключей).
Использует sounddevice (замена pyaudio — есть готовые сборки для Python 3.14).
"""
import numpy as np
import sounddevice as sd
import speech_recognition as sr


class Listener:
    def __init__(self, stt_cfg: dict):
        self.lang = stt_cfg.get("language", "ru-RU")
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.samplerate = 16000
        self.channels = 1
        self.device = None

    def _find_mic(self) -> bool:
        """Находит индекс устройства ввода (микрофона)."""
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d["max_input_channels"] > 0:
                    self.device = i
                    print(f"[Listener] Микрофон: {d['name']}")
                    return True
            print("[Listener] Микрофон не найден")
            return False
        except Exception as e:
            print(f"[Listener] Ошибка аудио: {e}")
            return False

    def calibrate(self) -> None:
        """Калибровка громкости по окружающему шуму (простая оценка RMS)."""
        if not self._find_mic():
            return
        try:
            print("[Listener] Калибрую... не говорите 2 секунды")
            duration = 1.5
            block = int(duration * self.samplerate)
            rec = sd.rec(block, samplerate=self.samplerate,
                         channels=self.channels, dtype="int16", device=self.device)
            sd.wait()
            rms = float(np.sqrt(np.mean(rec.astype(np.float32) ** 2)))
            self.recognizer.energy_threshold = max(200, int(rms * 1.5 + 100))
            print(f"[Listener] Порог шума: {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"[Listener] Ошибка калибровки: {e}")

    def listen_once(self, timeout: int = 6, phrase_limit: int = 15) -> str:
        """Слушает одну фразу. Возвращает текст в нижнем регистре или ''."""
        if not self._find_mic():
            return ""
        try:
            print("[Listener] Слушаю...")
            duration = min(phrase_limit, 10)
            rec = sd.rec(int(duration * self.samplerate),
                         samplerate=self.samplerate,
                         channels=self.channels, dtype="int16", device=self.device)
            sd.wait()
            if float(np.sqrt(np.mean(rec.astype(np.float32) ** 2))) < 20:
                print("[Listener] Слишком тихо")
                return ""
            audio = sr.AudioData(rec.tobytes(), self.samplerate, 2)
            text = self.recognizer.recognize_google(audio, language=self.lang)
            return text.lower().strip()
        except sr.UnknownValueError:
            print("[Listener] Речь не распознана")
            return ""
        except Exception as e:
            print(f"[Listener] Ошибка: {e}")
            return ""

    def listen_text_from_file(self, wav_path: str) -> str:
        """Распознавание из аудиофайла (для голосовых из Telegram)."""
        try:
            with sr.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)
            return self.recognizer.recognize_google(audio, language=self.lang).lower()
        except Exception:
            return ""
