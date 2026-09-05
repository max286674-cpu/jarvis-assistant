"""Low-latency microphone capture with local Whisper, optional Silero VAD and cloud fallback."""
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr

class Listener:
    def __init__(self, stt_cfg: dict):
        self.lang = stt_cfg.get("language", "ru-RU")
        self.engine = stt_cfg.get("engine", "auto").lower()
        self.vad_engine = stt_cfg.get("vad", "silero").lower()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = False
        self.samplerate = int(stt_cfg.get("sample_rate", 16000))
        self.channels = 1
        self.device = None
        self.start_threshold = float(stt_cfg.get("start_rms", 0.015))
        self.silence_threshold = float(stt_cfg.get("silence_rms", 0.008))
        self.start_timeout = float(stt_cfg.get("start_timeout", 6))
        self.max_phrase = float(stt_cfg.get("max_phrase_seconds", 15))
        self.silence_after_speech = float(stt_cfg.get("silence_after_speech", 0.8))
        self._local_stt = None
        self._silero = None
        if self.engine in ("auto", "faster-whisper"):
            try:
                from core.local_stt import LocalWhisperSTT
                self._local_stt = LocalWhisperSTT(self.lang, stt_cfg.get("whisper_model"))
                print("[Listener] faster-whisper backend доступен")
            except ImportError:
                if self.engine == "faster-whisper": print("[Listener] faster-whisper не установлен; используйте requirements-voice.txt")
        if self.vad_engine in ("auto", "silero"):
            try:
                from silero_vad import load_silero_vad
                self._silero = load_silero_vad()
                print("[Listener] Silero VAD доступен")
            except Exception as exc:
                if self.vad_engine == "silero": print(f"[Listener] Silero VAD недоступен, RMS fallback: {exc}")

    def _find_mic(self) -> bool:
        try:
            if self.device is not None: return True
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0:
                    self.device = i; print(f"[Listener] Микрофон: {d['name']}"); return True
            print("[Listener] Микрофон не найден"); return False
        except Exception as e:
            print(f"[Listener] Ошибка аудио: {e}"); return False

    def calibrate(self) -> None:
        if not self._find_mic(): return
        try:
            block = int(1.5 * self.samplerate)
            rec = sd.rec(block, samplerate=self.samplerate, channels=1, dtype="float32", device=self.device); sd.wait()
            rms = float(np.sqrt(np.mean(rec * rec)))
            self.start_threshold = max(rms * 3.0, 0.015)
            self.silence_threshold = max(rms * 1.8, 0.008)
            print(f"[Listener] RMS fallback thresholds: start={self.start_threshold:.4f}, silence={self.silence_threshold:.4f}")
        except Exception as e: print(f"[Listener] Ошибка калибровки: {e}")

    def _silero_has_speech(self, audio) -> bool:
        if self._silero is None: return False
        try:
            import torch
            from silero_vad import get_speech_timestamps
            tensor = torch.from_numpy(np.asarray(audio, dtype=np.float32))
            stamps = get_speech_timestamps(tensor, self._silero, sampling_rate=self.samplerate, threshold=0.45, min_speech_duration_ms=80, min_silence_duration_ms=80)
            return bool(stamps)
        except Exception:
            return False

    def _transcribe(self, audio):
        if self._local_stt is not None:
            try: return self._local_stt.transcribe(audio)
            except Exception as exc: print(f"[Listener] Local STT error: {exc}; fallback Google")
        pcm=(np.clip(audio,-1,1)*32767).astype(np.int16)
        data=sr.AudioData(pcm.tobytes(), self.samplerate, 2)
        return self.recognizer.recognize_google(data, language=self.lang).strip()

    def listen_once(self, start_timeout=None, silence_after_speech=None, max_phrase=None) -> str:
        if not self._find_mic(): return ""
        chunk_seconds = 0.08; chunk = int(self.samplerate * chunk_seconds)
        start_timeout = self.start_timeout if start_timeout is None else float(start_timeout)
        silence_after_speech = self.silence_after_speech if silence_after_speech is None else float(silence_after_speech)
        max_phrase = self.max_phrase if max_phrase is None else float(max_phrase)
        frames=[]; started=False; silence=0.0; started_at=None; deadline=time.monotonic()+start_timeout
        try:
            with sd.InputStream(samplerate=self.samplerate, channels=1, dtype="float32", device=self.device, blocksize=chunk) as stream:
                while True:
                    data, overflowed = stream.read(chunk)
                    if overflowed: print("[Listener] audio overflow")
                    rms=float(np.sqrt(np.mean(data * data)))
                    if not started:
                        if rms >= self.start_threshold:
                            started=True; started_at=time.monotonic(); frames.append(data.copy())
                        elif time.monotonic() >= deadline: return ""
                        continue
                    frames.append(data.copy())
                    if rms < self.silence_threshold: silence += chunk_seconds
                    else: silence=0.0
                    if silence >= silence_after_speech: break
                    if time.monotonic()-started_at >= max_phrase: break
            audio=np.concatenate(frames,axis=0).reshape(-1)
            if self._silero is not None and not self._silero_has_speech(audio): return ""
            return self._transcribe(audio)
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"[Listener] Ошибка: {e}"); return ""

    def listen_text_from_file(self, wav_path: str) -> str:
        if self._local_stt is not None:
            try:
                import soundfile as sf
                audio, rate = sf.read(wav_path, dtype="float32")
                if rate == self.samplerate: return self._local_stt.transcribe(audio)
            except Exception: pass
        try:
            with sr.AudioFile(wav_path) as source: audio=self.recognizer.record(source)
            return self.recognizer.recognize_google(audio, language=self.lang).strip()
        except Exception: return ""
