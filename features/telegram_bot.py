"""Telegram-интерфейс Jarvis с устойчивым long polling."""
import os, threading, time

class TelegramBot:
    def __init__(self,tg_cfg,jarvis):
        self.cfg=tg_cfg;self.jarvis=jarvis
        self.token=os.getenv("TELEGRAM_BOT_TOKEN",tg_cfg.get("bot_token","")).strip()
        self.chat_id=os.getenv("TELEGRAM_CHAT_ID",str(tg_cfg.get("chat_id","")).strip())
        self.enabled=bool(tg_cfg.get("enabled") and self.token and "ВСТАВЬ" not in self.token)
        if not self.enabled:print("[Telegram отключён: задайте TELEGRAM_BOT_TOKEN и enabled=true]")
    def send(self,text):
        if not self.enabled or not self.chat_id:return False
        try:
            import requests
            r=requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage",json={"chat_id":self.chat_id,"text":text},timeout=10);r.raise_for_status();return True
        except Exception as e:print(f"[Telegram send error: {e}]");return False
    def start_polling(self):
        if self.enabled:threading.Thread(target=self._poll,daemon=True,name="telegram-poll").start()
    def _poll(self):
        import requests
        offset=0
        while self.enabled:
            try:
                r=requests.get(f"https://api.telegram.org/bot{self.token}/getUpdates",params={"timeout":30,"offset":offset},timeout=40);r.raise_for_status()
                for upd in r.json().get("result",[]):
                    offset=upd["update_id"]+1;msg=upd.get("message",{});chat=str(msg.get("chat",{}).get("id",""))
                    if not self.chat_id:
                        self.chat_id=chat;self.cfg["chat_id"]=chat
                        try:
                            from core.config import CONFIG,save_json
                            CONFIG["telegram"]["chat_id"]=chat;save_json("config.json",CONFIG)
                        except Exception:pass
                    if chat!=str(self.chat_id):continue
                    text=msg.get("text","")
                    if text:self.send(self.jarvis.handle_text(text))
                    elif msg.get("voice"):self.send(self._handle_voice(msg["voice"]))
            except Exception as e:print(f"[TG poll: {e}]");time.sleep(3)
    def _handle_voice(self,voice):
        try:
            import requests,io
            from pydub import AudioSegment
            from core.listener import Listener
            info=requests.get(f"https://api.telegram.org/bot{self.token}/getFile",params={"file_id":voice["file_id"]},timeout=15).json()
            data=requests.get(f"https://api.telegram.org/file/bot{self.token}/{info['result']['file_path']}",timeout=30).content
            audio=AudioSegment.from_file(io.BytesIO(data));buf=io.BytesIO();audio.export(buf,format="wav");buf.seek(0)
            path="data/_telegram_voice.wav";open(path,"wb").write(buf.read())
            text=Listener({"language":"ru-RU"}).listen_text_from_file(path)
            return self.jarvis.handle_text(text) if text else "Не удалось распознать голосовое, сэр."
        except Exception as e:return f"Голосовое не разобрано: {e}"
