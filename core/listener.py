"""Слух Джарвиса: микрофон → текст (Google Web Speech, бесплатно, без ключей)."""
import speech_recognition as sr


class Listener:
    def __init__(self, stt_cfg: dict):
        self.lang = stt_cfg.get("language", "ru-RU")
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.mic = sr.Microphone()

    def calibrate(self) -> None:
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen_once(self, timeout: int = 6, phrase_limit: int = 15) -> str:
        """Слушает одну фразу. Возвращает текст в нижнем регистре или ''."""
        try:
            with self.mic as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
        except Exception:
            return ""
        try:
            text = self.recognizer.recognize_google(audio, language=self.lang)
            return text.lower().strip()
        except Exception:
            return ""

    def listen_text_from_file(self, wav_path: str) -> str:
        """Распознавание из аудиофайла (для голосовых из Telegram)."""
        try:
            with sr.AudioFile(wav_path) as source:
                audio = self.recognizer.record(source)
            return self.recognizer.recognize_google(audio, language=self.lang).lower()
        except Exception:
            return ""
