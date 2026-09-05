"""Optional local STT backend using faster-whisper; loaded lazily so base install stays lightweight."""
from __future__ import annotations
import os

class LocalWhisperSTT:
    def __init__(self, language="ru", model_name=None, device=None, compute_type=None):
        self.language = language.split("-")[0]
        self.model_name = model_name or os.getenv("JARVIS_WHISPER_MODEL", "small")
        self.device = device or os.getenv("JARVIS_WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("JARVIS_WHISPER_COMPUTE", "int8")
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        from faster_whisper import WhisperModel
        self._model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)

    def transcribe(self, audio_float32):
        self._load()
        segments, _ = self._model.transcribe(audio_float32, language=self.language, beam_size=1, vad_filter=True, condition_on_previous_text=False)
        return " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
