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
        self.router.attach(
            CryptoWatch(self.speaker, self.telegram), self.tenders,
        )

    def handle_text(self, text: str) -> str:
        answer = self.router.handle(text)
        return answer or "..."

    def speak(self, text: str) -> None:
        if text and text != "...":
            self.speaker.say(text)

    def proactive_loop(self) -> None:
        """Фоновые проактивные фичи: напоминания уже в своём потоке."""
        pcfg = CONFIG.get("proactive", {})
        eye_interval = pcfg.get("eye_rest_interval_min", 60) * 60
        last_eye = time.time()
        while True:
            time.sleep(30)
            if time.time() - last_eye > eye_interval:
                self.speak("Сэр, правило двадцати: 20 секунд смотрите вдаль. Глаза — тоже железо, но чинить их больнее.")
                last_eye = time.time()


def run_voice(jarvis: Jarvis) -> None:
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
    while True:
        text = listener.listen_once()
        if text:
            print(f"🗣 Вы: {text}")
            if any(w in text for w in ("выход", "отключись", "до свидания", "завершить работу")):
                jarvis.speak("Отключаюсь. Возвращайтесь, сэр.")
                break
            try:
                answer = jarvis.handle_text(text)
                jarvis.speak(answer)
            except Exception as e:
                print(f"[Ошибка обработки: {e}]")
                jarvis.speak("Что-то пошло не по протоколу, сэр.")


def run_text(jarvis: Jarvis) -> None:
    print("💬 Текстовый режим. Пишите команды ('выход' — выход).")
    jarvis.speak("Джарвис на связи, сэр. Текстовый канал активен.")
    while True:
        try:
            text = input("Вы: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("выход", "exit"):
            break
        answer = jarvis.handle_text(text)
        jarvis.speak(answer)


def check_config(jarvis: Jarvis) -> None:
    print("=== Диагностика Джарвиса ===")
    brain_ok = jarvis.brain.enabled
    tg_ok = jarvis.telegram.enabled
    print(f"Мозг Gemini:      {'✅ подключён' if brain_ok else '❌ нет ключа (config.json → brain.api_key)'}")
    print(f"Telegram:         {'✅ включён' if tg_ok else '⚪ отключён (config.json → telegram)'}")
    print(f"Голос:            {CONFIG.get('voice', {}).get('tts_voice')}")
    print(f"Кодовое слово:    {CONFIG.get('session', {}).get('restore_command')}")
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
