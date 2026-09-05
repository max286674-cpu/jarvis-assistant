"""Telegram-интерфейс Jarvis: long polling, текст и голос."""
import os, threading, time, tempfile
from pathlib import Path
from core.config import data_file

class TelegramBot:
    def __init__(self,tg_cfg,jarvis):
        self.cfg=tg_cfg; self.jarvis=jarvis
        self.token=os.getenv("TELEGRAM_BOT_TOKEN",tg_cfg.get("bot_token","")).strip()
        self.chat_id=os.getenv("TELEGRAM_CHAT_ID",str(tg_cfg.get("chat_id","")).strip())
        self.enabled=bool(tg_cfg.get("enabled") and self.token and "ВСТАВЬ" not in self.token)
        self.offset_path=data_file("telegram_offset.txt")
        self._send_lock=threading.Lock()
        if not self.enabled: print("[Telegram отключён: задайте TELEGRAM_BOT_TOKEN и enabled=true]")

    def send(self,text):
        if not self.enabled or not self.chat_id or not text: return False
        try:
            import requests
            text=str(text)
            chunks=[text[i:i+3900] for i in range(0,len(text),3900)]
            with self._send_lock:
                for chunk in chunks:
                    r=requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage",json={"chat_id":self.chat_id,"text":chunk},timeout=10); r.raise_for_status()
            return True
        except Exception as e: print(f"[Telegram send error: {e}]"); return False

    def start_polling(self):
        if self.enabled: threading.Thread(target=self._poll,daemon=True,name="telegram-poll").start()

    def _load_offset(self):
        try: return int(self.offset_path.read_text().strip())
        except Exception: return 0

    def _save_offset(self,offset):
        try:
            self.offset_path.parent.mkdir(parents=True,exist_ok=True); self.offset_path.write_text(str(offset),encoding="utf-8")
        except Exception: pass

    def _poll(self):
        import requests
        offset=self._load_offset()
        while self.enabled:
            try:
                r=requests.get(f"https://api.telegram.org/bot{self.token}/getUpdates",params={"timeout":30,"offset":offset,"allowed_updates":["message"]},timeout=40); r.raise_for_status()
                for upd in r.json().get("result",[]):
                    offset=upd.get("update_id",offset-1)+1; self._save_offset(offset)
                    msg=upd.get("message",{}); chat=str(msg.get("chat",{}).get("id",""))
                    if not self.chat_id:
                        self.chat_id=chat; self.cfg["chat_id"]=chat
                        try:
                            from core.config import CONFIG,save_json
                            CONFIG.setdefault("telegram",{})["chat_id"]=chat; save_json("config.json",CONFIG)
                        except Exception: pass
                    if chat!=str(self.chat_id): continue
                    text=msg.get("text","")
                    if text: self.send(self.jarvis.handle_text(text))
                    elif msg.get("voice"): self.send(self._handle_voice(msg["voice"]))
            except Exception as e: print(f"[TG poll: {e}]"); time.sleep(3)

    def _handle_voice(self,voice):
        path=None
        try:
            import requests,io
            from pydub import AudioSegment
            from core.listener import Listener
            info=requests.get(f"https://api.telegram.org/bot{self.token}/getFile",params={"file_id":voice["file_id"]},timeout=15).json()
            if not info.get("ok"): return "Не удалось получить голосовое, сэр."
            data=requests.get(f"https://api.telegram.org/file/bot{self.token}/{info['result']['file_path']}",timeout=30).content
            audio=AudioSegment.from_file(io.BytesIO(data)); buf=io.BytesIO(); audio.export(buf,format="wav")
            with tempfile.NamedTemporaryFile(prefix="jarvis_tg_",suffix=".wav",dir=str(data_file(".").parent),delete=False) as f:
                f.write(buf.getvalue()); path=f.name
            text=Listener({"language":"ru-RU"}).listen_text_from_file(path)
            return self.jarvis.handle_text(text) if text else "Не удалось распознать голосовое, сэр."
        except Exception as e: return f"Голосовое не разобрано: {e}"
        finally:
            if path:
                try: Path(path).unlink(missing_ok=True)
                except Exception: pass
