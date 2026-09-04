"""
ДЖАРВИС — персональный AI-ассистент для Windows 11.
Запуск:  python jarvis.py          (голосовой режим)
         python jarvis.py --text   (текстовый режим, для теста без микрофона)
         python jarvis.py --check  (проверка конфигурации)
"""
import sys
import threading
import time

from core.config import CONFIG
from core.speaker import Speaker
from core.actions import ActionExecutor
from core.brain import Brain
from core.system_control import SystemControl
from core.router import Router
from features.sessions import SessionManager
from features.reminders import ReminderEngine
from features.code_helper import CodeHelper
from features.telegram_bot import TelegramBot
from features.crypto_watch import CryptoWatch
from features.tenders import TenderRadar


class Jarvis:
    """Собирает все модули вместе. handle_text() — единая точка входа."""

    def __init__(self):
        self.speaker = Speaker(CONFIG.get("voice", {}))
        self.executor = ActionExecutor(self.speaker)
        self.sessions = SessionManager(self.speaker)
        self.reminders = ReminderEngine(self.speaker)
        self.brain = Brain(CONFIG.get("brain", {}), CONFIG.get("user", {}).get("name", "Сэр"))
        self.code_helper = CodeHelper(self.brain)
        self.telegram = TelegramBot(CONFIG.get("telegram", {}), self)
        self.router = Router(
            self.speaker, self.executor, self.sessions,
            self.reminders, self.brain, self.code_helper, self.telegram,
        )
        self.tenders = TenderRadar(self.speaker, self.telegram)
        self.router.attach(CryptoWatch(self.speaker, self.telegram), self.tenders)

    def handle_text(self, text: str) -> str:
        return self.router.handle(text)

    def speak(self, text: str) -> None:
        if text and text != "...":
            self.speaker.say(text)

    def proactive_loop(self) -> None:
        pcfg = CONFIG.get("proactive", {})
        eye_interval = pcfg.get("eye_rest_interval_min", 60) * 60
        last_eye = time.time()
        while True:
            time.sleep(30)
            if time.time() - last_eye > eye_interval:
                self.speak("Сэр, правило двадцати: 20 секунд смотрите вдаль. Глаза — тоже железо, но чинить их больнее.")
                last_eye = time.time()


def run_voice(jarvis: Jarvis) -> None:
    import threading
    from core.listener import Listener
    listener = Listener(CONFIG.get("stt", {}))
    print("🎤 Калибрую микрофон... не говорите 2 секунды")
    try:
        listener.calibrate()
    except Exception as e:
        print(f"[Микрофон недоступен: {e}. Запустите: python jarvis.py --text]")
        sys.exit(1)
    jarvis.speak("Джарвис на связи, сэр. Все системы в норме.")
    print("✅ Слушаю... (Ctrl+C — выход)")

    # Параллельное прослушивание: слушаем даже во время речи
    listening_active = threading.Event()
    listening_active.set()

    def listen_loop():
        while listening_active.is_set():
            try:
                text = listener.listen_once()
                if text:
                    print(f"🗣 Вы: {text}")
                    # Прерывание речи
                    if any(w in text.lower() for w in ("стоп", "молчи", "тихо", "замолчи", "хватит")):
                        jarvis.speaker.stop()
                        jarvis.speak("Останавливаюсь, сэр.")
                        continue
                    # Выход
                    if any(w in text.lower() for w in ("выход", "отключись", "до свидания", "завершить работу")):
                        jarvis.speak("Отключаюсь. Возвращайтесь, сэр.")
                        listening_active.clear()
                        break
                    # Команды управления
                    if any(w in text.lower() for w in ("скриншот", "сделай фото")):
                        ans = jarvis.speaker.screenshot()
                        jarvis.speak(ans)
                        continue
                    if any(w in text.lower() for w in ("браузер", "открой браузер")):
                        ans = jarvis.speaker.open_browser()
                        jarvis.speak(ans)
                        continue
                    if any(w in text.lower() for w in ("закрыть браузер")):
                        import webbrowser
                        webbrowser.get().close()
                        jarvis.speak("Закрываю браузер, сэр.")
                        continue
                    # Обработка через мозг
                    try:
                        answer = jarvis.handle_text(text)
                        jarvis.speak(answer)
                    except Exception as e:
                        print(f"[Ошибка обработки: {e}]")
                        jarvis.speak("Что-то пошло не по протоколу, сэр.")
            except Exception as e:
                print(f"[Ошибка прослушивания: {e}]")

    listener_thread = threading.Thread(target=listen_loop, daemon=True)
    listener_thread.start()

    # Основной поток — просто держим программу живой
    try:
        while listening_active.is_set():
            threading.Event().wait(0.5)
    except KeyboardInterrupt:
        listening_active.clear()
        jarvis.speak("Отключаюсь. Возвращайтесь, сэр.")


def run_text(jarvis: Jarvis) -> None:
    print("💬 Текстовый режим. Пишите команды ('выход' — выход).")
    while True:
        try:
            text = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("выход", "exit"):
            break
        try:
            print(f"Джарвис: {jarvis.handle_text(text)}")
        except Exception as e:
            print(f"[Ошибка: {e}]")


def check_config(jarvis: Jarvis) -> None:
    print("=== Диагностика Джарвиса ===")
    print(f"LLM provider:      {jarvis.brain.provider}")
    print(f"LLM status:        {'✅ OpenRouter подключён' if jarvis.brain.enabled else '❌ нет OPENROUTER_API_KEY'}")
    print(f"Routing model:     {jarvis.brain.selected_model('проверка обычного запроса')}")
    print(f"Telegram:          {'✅ включён' if jarvis.telegram.enabled else '⚪ отключён'}")
    print(f"Голос:             {CONFIG.get('voice', {}).get('tts_voice')}")
    print(f"Кодовое слово:     {CONFIG.get('session', {}).get('restore_command')}")
    print("Готов к работе, сэр.")


if __name__ == "__main__":
    j = Jarvis()
    j.telegram.start_polling()
    threading.Thread(target=j.proactive_loop, daemon=True).start()
    if "--check" in sys.argv:
        check_config(j)
    elif "--text" in sys.argv:
        run_text(j)
    else:
        run_voice(j)
