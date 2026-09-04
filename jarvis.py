"""Jarvis entry point. Voice-first agent with interruptible full-duplex TTS."""
import sys, threading, time
from core.config import CONFIG
from core.duplex_speaker import DuplexSpeaker
from core.actions import ActionExecutor
from core.agent_tools import Tool, build_default_registry
from core.brain import Brain
from core.router import Router
from core.web_search import search_web
from features.sessions import SessionManager
from features.reminders import ReminderEngine
from features.code_helper import CodeHelper
from features.telegram_bot import TelegramBot
from features.crypto_watch import CryptoWatch
from features.tenders import TenderRadar
from features.briefing import full_briefing, get_joke, get_system_stats, get_weather, get_currency, translate, get_crypto
from features.news import get_news, day_digest

class Jarvis:
    def __init__(self):
        self.speaker = DuplexSpeaker(CONFIG.get("voice", {})); self.executor = ActionExecutor(self.speaker)
        self.sessions = SessionManager(self.speaker); self.reminders = ReminderEngine(self.speaker)
        self.telegram = TelegramBot(CONFIG.get("telegram", {}), self)
        self.tenders = TenderRadar(self.speaker, self.telegram); self.crypto_watch = CryptoWatch(self.speaker, self.telegram)
        self.tools = build_default_registry(self.executor, self.reminders, self.telegram if self.telegram.enabled else None, search_web)
        self._register_features()
        self.brain = Brain(CONFIG.get("brain", {}), CONFIG.get("user", {}).get("name", "Сэр"), self.tools)
        self.code_helper = CodeHelper(self.brain)
        self.router = Router(self.speaker, self.executor, self.sessions, self.reminders, self.brain, self.code_helper, self.telegram)
        self.router.attach(self.crypto_watch, self.tenders)

    def _register_features(self):
        def reg(name, desc, props, fn, required=None, risk="safe"):
            schema={"type":"object","properties":props}
            if required: schema["required"]=required
            self.tools.register(Tool(name, desc, schema, fn, risk))
        reg("weather","Получить текущую погоду", {"city":{"type":"string"}}, get_weather,["city"])
        reg("currency_rates","Получить актуальные курсы валют",{},get_currency)
        reg("crypto_price","Получить актуальные цены криптовалют",{},get_crypto)
        reg("world_news","Получить свежую мировую сводку",{},day_digest)
        reg("news_category","Получить свежие новости категории world/belarus/crypto/tech",{"category":{"type":"string"}},get_news,["category"])
        reg("system_status","Показать состояние компьютера",{},get_system_stats)
        reg("joke","Рассказать короткую шутку",{},get_joke)
        reg("translate","Перевести текст",{"text":{"type":"string"},"language":{"type":"string","enum":["en","ru"]}},translate,["text"])
        reg("create_task","Добавить задачу",{"text":{"type":"string"}},self.reminders.add_task,["text"])
        reg("morning_briefing","Собрать утренний брифинг",{},lambda: full_briefing(self.reminders.morning_tasks(),tenders=self.tenders))
        reg("crypto_watch","Добавить крипто-наблюдение",{"instruction":{"type":"string"}},self.crypto_watch.add,["instruction"])
        reg("crypto_watches","Показать крипто-наблюдения",{},self.crypto_watch.list_watches)
        reg("clear_crypto_watches","Удалить крипто-наблюдения",{},self.crypto_watch.clear,risk="confirm")
        reg("tender_watch","Настроить тендерный радар",{"instruction":{"type":"string"}},self.tenders.set_keywords,["instruction"])
        reg("check_tenders","Проверить новые тендеры",{},self.tenders.daily_check)

    def handle_text(self, text):
        return self.router.handle(text)

    def speak(self, text, blocking=True):
        if text and text != "...":
            self.speaker.say(text, blocking=blocking)

    def proactive_loop(self):
        interval=int(CONFIG.get("proactive",{}).get("eye_rest_interval_min",60))*60; last=time.monotonic()
        while True:
            time.sleep(15)
            if time.monotonic()-last>=interval:
                self.speak("Небольшой перерыв для глаз.", blocking=False); last=time.monotonic()

def run_voice(j):
    from core.listener import Listener
    listener=Listener(CONFIG.get("stt",{}))
    try: listener.calibrate()
    except Exception as e: print(f"Микрофон недоступен: {e}"); sys.exit(1)
    j.speak("Джарвис на связи. Говорите.")
    while True:
        text=listener.listen_once()
        if not text: continue
        print("Вы:",text)
        low=text.lower().strip()
        if low in ("выход","отключись","до свидания","завершить работу"):
            j.speak("Отключаюсь."); break
        try:
            answer=j.handle_text(text)
            if answer == "...":
                j.speaker.stop(); continue
            # Озвучка идёт в отдельном потоке. Микрофон остаётся активным и может перебить ответ.
            j.speak(answer, blocking=False)
            while j.speaker.speaking:
                interruption = listener.listen_once()
                if interruption:
                    print("Перебивание:", interruption)
                    j.speaker.stop()
                    if interruption.lower().strip() in ("выход", "отключись"):
                        j.speak("Отключаюсь."); return
                    followup = j.handle_text(interruption)
                    j.speak(followup, blocking=False)
        except Exception as e:
            print("Ошибка:",e)

def run_text(j):
    while True:
        try: text=input("Вы: ").strip()
        except (EOFError,KeyboardInterrupt): break
        if text.lower() in ("выход","exit"): break
        if text: print("Джарвис:",j.handle_text(text))

def check_config(j):
    print("LLM:","OK" if j.brain.enabled else "ERROR",j.brain.models.get("main"))
    print("Tools:",", ".join(j.tools.names()))
    print("Telegram:","OK" if j.telegram.enabled else "OFF")
    print("Voice: full-duplex / interruptible TTS")

if __name__=="__main__":
    j=Jarvis(); j.telegram.start_polling(); threading.Thread(target=j.proactive_loop,daemon=True).start()
    if "--check" in sys.argv: check_config(j)
    elif "--text" in sys.argv: run_text(j)
    else: run_voice(j)
