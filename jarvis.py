"""Jarvis entry point: voice-first agent with explicit runtime state and barge-in."""
import re, sys, threading, time
from core.config import CONFIG
from core.duplex_speaker import DuplexSpeaker
from core.actions import ActionExecutor
from core.agent_tools import Tool, build_default_registry
from core.brain import Brain
from core.router import Router
from core.state import RuntimeState, RuntimeStateMachine, CancellationToken
from core.workspace import Workspace
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
        self.state = RuntimeStateMachine(); self.cancel = CancellationToken()
        self.speaker = DuplexSpeaker(CONFIG.get("voice", {})); self.executor = ActionExecutor(self.speaker)
        self.sessions = SessionManager(self.speaker); self.reminders = ReminderEngine(self.speaker)
        self.telegram = TelegramBot(CONFIG.get("telegram", {}), self)
        self.tenders = TenderRadar(self.speaker, self.telegram); self.crypto_watch = CryptoWatch(self.speaker, self.telegram)
        self.workspace = Workspace(CONFIG.get("workspace", {}).get("roots"))
        self.browser = None
        try:
            from core.browser import BrowserAgent
            self.browser = BrowserAgent()
        except ImportError:
            pass
        self.tools = build_default_registry(self.executor, self.reminders, self.telegram if self.telegram.enabled else None, search_web)
        self._register_features()
        self.brain = Brain(CONFIG.get("brain", {}), CONFIG.get("user", {}).get("name", "Сэр"), self.tools)
        self._register_memory_tools(); self._register_computer_tools()
        self.code_helper = CodeHelper(self.brain)
        self.router = Router(self.speaker, self.executor, self.sessions, self.reminders, self.brain, self.code_helper, self.telegram)
        self.router.attach(self.crypto_watch, self.tenders)

    def _register_memory_tools(self):
        self.tools.register(Tool("remember_memory", "Сохранить явно указанный пользователем полезный факт в долговременную память", {"type":"object","properties":{"text":{"type":"string"},"category":{"type":"string"}},"required":["text"]}, self.brain.remember))
        self.tools.register(Tool("clear_memory", "Очистить долговременную память", {"type":"object","properties":{}}, self.brain.forget_memory, "confirm"))

    def _register_computer_tools(self):
        self.tools.register(Tool("list_files", "Показать файлы в разрешённой рабочей папке", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, self.workspace.list_dir))
        self.tools.register(Tool("read_file", "Прочитать текстовый файл в разрешённой рабочей папке", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, self.workspace.read_text))
        self.tools.register(Tool("write_file", "Создать или перезаписать текстовый файл в разрешённой рабочей папке", {"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}, self.workspace.write_text, "confirm"))
        self.tools.register(Tool("delete_file", "Удалить файл из разрешённой рабочей папки", {"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}, self.workspace.delete, "dangerous"))
        if self.browser:
            self.tools.register(Tool("browser_open", "Открыть страницу через Playwright", {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}, self.browser.open))
            self.tools.register(Tool("browser_snapshot", "Прочитать видимый текст текущей страницы", {"type":"object","properties":{}}, self.browser.snapshot))
            self.tools.register(Tool("browser_close", "Закрыть браузерный агент", {"type":"object","properties":{}}, self.browser.close))

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

    def handle_text(self, text): return self.router.handle(text)

    def speak(self, text, blocking=True):
        if text and text != "...":
            self.state.set(RuntimeState.SPEAKING); self.speaker.say(text, blocking=blocking)
            if blocking: self.state.set(RuntimeState.IDLE)

    def proactive_loop(self):
        interval=int(CONFIG.get("proactive",{}).get("eye_rest_interval_min",60))*60; last=time.monotonic()
        while True:
            time.sleep(15)
            if time.monotonic()-last>=interval:
                self.speak("Небольшой перерыв для глаз.", blocking=False); last=time.monotonic()

def _is_tts_echo(text, spoken):
    if not text or not spoken: return False
    words=lambda s:set(re.findall(r"[а-яёa-z0-9]{4,}", s.lower()))
    heard, source=words(text), words(spoken)
    if not heard or not source: return False
    return len(heard & source) / len(heard) >= 0.70

def run_voice(j):
    from core.listener import Listener
    listener=Listener(CONFIG.get("stt",{}))
    try: listener.calibrate()
    except Exception as e: print(f"Микрофон недоступен: {e}"); sys.exit(1)
    j.speak("Джарвис на связи. Говорите."); last_answer=""
    while True:
        j.state.set(RuntimeState.LISTENING); text=listener.listen_once()
        if not text: continue
        print("Вы:",text); low=text.lower().strip()
        if low in ("выход","отключись","до свидания","завершить работу"):
            j.speak("Отключаюсь."); j.state.stop(); break
        try:
            j.state.set(RuntimeState.THINKING); j.cancel.reset(); answer=j.handle_text(text)
            if answer == "...": j.speaker.stop(); j.state.set(RuntimeState.IDLE); continue
            last_answer=answer; j.state.set(RuntimeState.SPEAKING); j.speak(answer, blocking=False)
            while j.speaker.speaking:
                interruption=listener.listen_once(start_timeout=0.35, silence_after_speech=0.35, max_phrase=8)
                if not interruption: continue
                if _is_tts_echo(interruption,last_answer): continue
                print("Перебивание:",interruption); j.state.interrupt(); j.cancel.cancel(); j.speaker.stop()
                if interruption.lower().strip() in ("выход","отключись"):
                    j.speak("Отключаюсь."); j.state.stop(); return
                j.state.set(RuntimeState.THINKING); j.cancel.reset(); last_answer=j.handle_text(interruption)
                j.state.set(RuntimeState.SPEAKING); j.speak(last_answer,blocking=False)
            j.state.set(RuntimeState.IDLE)
        except Exception as e:
            j.state.set(RuntimeState.ERROR); print("Ошибка:",e)

def run_text(j):
    while True:
        try: text=input("Вы: ").strip()
        except (EOFError,KeyboardInterrupt): break
        if text.lower() in ("выход","exit"): break
        if text: print("Джарвис:",j.handle_text(text))

def check_config(j):
    print("LLM:","OK" if j.brain.enabled else "ERROR",j.brain.models.get("main")); print("Tools:",", ".join(j.tools.names())); print("Telegram:","OK" if j.telegram.enabled else "OFF"); print("Voice: state-machine + interruptible full-duplex TTS")

if __name__=="__main__":
    j=Jarvis(); j.telegram.start_polling(); threading.Thread(target=j.proactive_loop,daemon=True).start()
    if "--check" in sys.argv: check_config(j)
    elif "--text" in sys.argv: run_text(j)
    else: run_voice(j)
