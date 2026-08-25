"""Telegram: управление Джарвисом с телефона + push-уведомления."""
import threading


class TelegramBot:
    def __init__(self, tg_cfg: dict, jarvis):
        """jarvis — объект с методом handle_text(text) -> str."""
        self.cfg = tg_cfg
        self.jarvis = jarvis
        self.enabled = (
            tg_cfg.get("enabled")
            and "ВСТАВЬ" not in tg_cfg.get("bot_token", "")
        )
        if not self.enabled:
            print("[Telegram отключён: не задан токен]")
            return

    def send(self, text: str) -> None:
        """Push-уведомление пользователю в чат."""
        if not self.enabled:
            return
        try:
            import requests
            chat_id = self.cfg.get("chat_id", "")
            if not chat_id:
                return
            url = f"https://api.telegram.org/bot{self.cfg['bot_token']}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        except Exception as e:
            print(f"[Telegram send error: {e}]")

    def start_polling(self) -> None:
        if not self.enabled:
            return
        threading.Thread(target=self._poll, daemon=True).start()

    def _poll(self) -> None:
        try:
            import requests
            token = self.cfg["bot_token"]
            offset = 0
            while True:
                try:
                    url = f"https://api.telegram.org/bot{token}/getUpdates"
                    r = requests.get(
                        url,
                        params={"timeout": 30, "offset": offset},
                        timeout=40,
                    ).json()
                    for upd in r.get("result", []):
                        offset = upd["update_id"] + 1
                        msg = upd.get("message", {})
                        chat_id = str(msg.get("chat", {}).get("id", ""))
                        # сохраняем chat_id при первом контакте
                        if not self.cfg.get("chat_id"):
                            from core.config import save_json, CONFIG
                            CONFIG["telegram"]["chat_id"] = chat_id
                            save_json("config.json", CONFIG)
                            self.cfg["chat_id"] = chat_id
                            self.send("Канал связи установлен. Джарвис на связи, сэр.")
                            continue
                        if chat_id != str(self.cfg.get("chat_id")):
                            continue  # чужие не обслуживаем
                        voice = msg.get("voice")
                        text = msg.get("text", "")
                        if voice:
                            answer = self._handle_voice(token, voice)
                        elif text:
                            answer = self.jarvis.handle_text(text)
                        else:
                            answer = "Сэр, я понимаю текст и голосовые сообщения."
                        self.send(answer)
                except Exception as e:
                    print(f"[TG poll: {e}]")
        except ImportError:
            print("[Для Telegram нужен pip install requests]")

    def _handle_voice(self, token: str, voice: dict) -> str:
        """Скачивает голосовое и распознаёт через Listener."""
        try:
            import requests, io, wave
            from core.listener import Listener
            file_id = voice["file_id"]
            info = requests.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={"file_id": file_id}, timeout=15,
            ).json()
            path = info["result"]["file_path"]
            ogg = requests.get(
                f"https://api.telegram.org/file/bot{token}/{path}", timeout=30
            ).content
            # конвертация ogg→wav требует ffmpeg; пробуем pydub
            from pydub import AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(ogg))
            buf = io.BytesIO()
            audio.export(buf, format="wav")
            buf.seek(0)
            listener = Listener({"language": "ru-RU"})
            with wave.open(buf) as w:
                pass
            import speech_recognition as sr
            rec = sr.Recognizer()
            with sr.AudioFile(buf) as source:
                audio_data = rec.record(source)
            text = rec.recognize_google(audio_data, language="ru-RU").lower()
            return self.jarvis.handle_text(text)
        except Exception as e:
            return f"Голосовое не разобрал (нужен ffmpeg в системе): {e}"
