"""Голосовой ввод: sounddevice + простая локальная VAD-логика + Google STT.
Не записывает фиксированные 10 секунд: ждёт начало речи и завершает запись после паузы.
"""
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr

class Listener:
    def __init__(self, stt_cfg: dict):
        self.lang = stt_cfg.get("language", "ru-RU")
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = False
        self.samplerate = int(stt_cfg.get("sample_rate", 16000))
        self.channels = 1
        self.device = None
        self.start_threshold = float(stt_cfg.get("start_rms", 450))
        self.silence_threshold = float(stt_cfg.get("silence_rms", 260))
        self.start_timeout = float(stt_cfg.get("start_timeout", 6))
        self.max_phrase = float(stt_cfg.get("max_phrase_seconds", 15))
        self.silence_after_speech = float(stt_cfg.get("silence_after_speech", 0.8))

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
            # float32 PCM имеет диапазон [-1, 1]. Порог не должен становиться нереалистичным.
            self.start_threshold = max(rms * 3.0, 0.015)
            self.silence_threshold = max(rms * 1.8, 0.008)
            print(f"[Listener] VAD thresholds: start={self.start_threshold:.4f}, silence={self.silence_threshold:.4f}")
        except Exception as e: print(f"[Listener] Ошибка калибровки: {e}")

    def listen_once(self) -> str:
        if not self._find_mic(): return ""
        chunk_seconds = 0.20; chunk = int(self.samplerate * chunk_seconds)
        frames=[]; started=False; silence=0.0; started_at=None; deadline=time.monotonic()+self.start_timeout
        try:
            print("[Listener] Слушаю...")
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
                    if silence >= self.silence_after_speech: break
                    if time.monotonic()-started_at >= self.max_phrase: break
            audio=np.concatenate(frames,axis=0)
            pcm=np.clip(audio,-1,1); pcm=(pcm*32767).astype(np.int16)
            data=sr.AudioData(pcm.tobytes(), self.samplerate, 2)
            text=self.recognizer.recognize_google(data, language=self.lang)
            return text.strip()
        except sr.UnknownValueError:
            print("[Listener] Речь не распознана"); return ""
        except Exception as e:
            print(f"[Listener] Ошибка: {e}"); return ""

    def listen_text_from_file(self, wav_path: str) -> str:
        try:
            with sr.AudioFile(wav_path) as source: audio=self.recognizer.record(source)
            return self.recognizer.recognize_google(audio, language=self.lang).strip()
        except Exception: return ""
