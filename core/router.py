"""Маршрутизатор: сопоставляет фразу пользователя с командой или действием."""
import re

from core.config import COMMANDS, save_json, CONFIG
from features.briefing import (
    full_briefing, get_joke, get_system_stats, get_weather, get_currency,
    translate, get_crypto,
)
from features.news import get_news, day_digest
from features.crypto_watch import CryptoWatch
from features.tenders import TenderRadar
from features.ai_tutor import AiTutor


class Router:
    def __init__(self, speaker, executor, sessions, reminders, brain, code_helper, telegram=None):
        self.speaker = speaker
        self.executor = executor
        self.sessions = sessions
        self.reminders = reminders
        self.brain = brain
        self.code_helper = code_helper
        self.telegram = telegram
        self.crypto_watch = None
        self.tenders = None
        self.tutor = AiTutor(brain)

    def attach(self, crypto_watch, tenders):
        """Подключает фоновые сервисы после создания Jarvis."""
        self.crypto_watch = crypto_watch
        self.tenders = tenders
        self.learning_state = None  # для голосового добавления команд

    def handle(self, text: str) -> str:
        """Главная точка входа: фраза → ответ/действие."""
        low = text.lower().strip()
        if not low:
            return ""

        # --- режим обучения новой команды ---
        if self.learning_state == "await_phrases":
            self.learning_state = None
            phrases = [p.strip() for p in low.split(",") if p.strip()]
            self._pending_cmd["phrases"] = phrases
            self.learning_state = "await_actions"
            self._pending_name = phrases[0].replace(" ", "_")[:20]
            return ("Фразы записал. Теперь назовите действия через запятую "
                    "в формате: открыть приложение код / открыть сайт youtube.com / сказать готово")
        if self.learning_state == "await_actions":
            self.learning_state = None
            actions = []
            for part in low.split(","):
                part = part.strip()
                m_app = re.match(r"(?:открыть|запусти\w*)\s+приложени\w+\s+(.+)", part)
                m_site = re.match(r"(?:открыть|открой)\s+сайт\s+(\S+)", part)
                m_folder = re.match(r"(?:открыть|открой)\s+папку\s+(.+)", part)
                m_say = re.match(r"сказать\s+(.+)", part)
                if m_app:
                    actions.append({"type": "open_app", "target": m_app.group(1)})
                elif m_site:
                    actions.append({"type": "open_url", "target": m_site.group(1)})
                elif m_folder:
                    actions.append({"type": "open_folder", "target": m_folder.group(1)})
                elif m_say:
                    actions.append({"type": "say", "target": m_say.group(1)})
            if not actions:
                return "Действий не распознал, сэр. Команда отменена."
            name = getattr(self, "_pending_name", "custom")
            COMMANDS.setdefault("custom", {})[name] = {
                "phrases": self._pending_cmd["phrases"], "actions": actions,
            }
            save_json("commands.json", COMMANDS)
            return f"Команда «{name}» сохранена. Как всегда безупречно — это я."

        # --- запомнить команду ---
        if re.search(r"(запомни команду|создай команду|новая команда|добавь команду)", low):
            self.learning_state = "await_phrases"
            self._pending_cmd = {}
            return ("Слушаю. Назовите фразы активации через запятую, "
                    "например: включи работу, за работу")

        # --- кодовые слова сессий ---
        restore_words = CONFIG["session"].get("restore_command", ["я готов работать"])
        rest_words = CONFIG["session"].get("rest_command", ["давай отдохнём"])
        if any(w in low for w in restore_words):
            reply = self.sessions.restore(self.executor)
            return reply + " Рабочий режим активирован, сэр."
        if any(w in low for w in rest_words):
            res = ""
            for cmd in ("rest_mode",):
                cfg = COMMANDS.get(cmd, {})
                for action in cfg.get("actions", []):
                    res += self.executor.run(action) + " "
            return res + "Отдыхаем, сэр. Я никому не скажу, что вы это заслужили."

        # --- сохранить сессию ---
        if "сохрани сессию" in low or "сохранить сессию" in low:
            return self.sessions.save_current()

        # --- напоминания и задачи ---
        if low.startswith(("напомни", "поставь напоминание")):
            return self.reminders.parse_and_add(low)
        if low.startswith(("добавь задачу", "новая задача")):
            return self.reminders.add_task(low)
        if "мои задачи" in low or "список задач" in low or "что в плане" in low:
            return self.reminders.list_tasks()
        m = re.match(r"задача\s*(\d+)\s*(выполнена|сделана|готова|закрыта)", low)
        if m:
            return self.reminders.done_task(int(m.group(1)))

        # --- брифинг и справка ---
        if re.search(r"(что у нас|брифинг|доброе утро|как дела сегодня|начнём день)", low):
            return full_briefing(self.reminders.morning_tasks(), tenders=self.tenders)
        if "погода" in low:
            city = "Moscow"
            m = re.search(r"погод\w*\s+в\s+(\S+)", low)
            if m:
                city = m.group(1)
            return get_weather(city)
        if any(w in low for w in ("курс валют", "курс доллара", "доллар", "евро")) and "курс" in low:
            return get_currency()
        if any(w in low for w in ("биткоин", "крипт", "эфир", "bitcoin")):
            return get_crypto()
        # --- крипто-сторож ---
        if re.search(r"(следи|наблюдай|мониторь).*(биткоин|эфир|тон|солан|bitcoin)", low):
            return self.crypto_watch.add(low) if self.crypto_watch else "Сторож не запущен."
        if "мои наблюдения" in low or "что следишь" in low:
            return self.crypto_watch.list_watches() if self.crypto_watch else "Сторож не запущен."
        if "сними наблюдения" in low or "останови слежку" in low:
            return self.crypto_watch.clear() if self.crypto_watch else "Сторож не запущен."

        # --- тендеры ---
        if "следи за тендерами" in low or "тендеры по словам" in low:
            return self.tenders.set_keywords(low) if self.tenders else "Радар не запущен."
        if "новые тендеры" in low or "тендерный радар" in low:
            res = self.tenders.daily_check() if self.tenders else ""
            return res or "Свежих тендеров по вашим словам нет, сэр."

        # --- учебник нейросетей ---
        if re.search(r"(урок|обучи|курс).*(нейросет|ии|искусственн)|следующ(ий|ая) урок", low):
            return self.tutor.lesson(text)
        if any(w in low for w in ("новости дня", "сводка", "что в мире", "что происходит")):
            return day_digest() or "Новостей нет, сэр. Подозрительно тихо."
        if "новости беларус" in low:
            return get_news("belarus")
        if "новости крипт" in low or "крипто новости" in low:
            return get_news("crypto")
        if "новости технологий" in low or "новости ит" in low:
            return get_news("tech")
        if "новости" in low:
            return get_news("world")
        if "новости" in low and ("нейросет" in low or "ии" in low or "ai" in low):
            self.executor.open_url("https://habr.com/ru/hubs/ai/")
            return "Открываю свежие новости из мира ИИ, сэр."
        if re.search(r"(как себя чувствует система|состояние системы|диагностика|статус системы)", low):
            return get_system_stats()
        if "шутк" in low or "рассмеши" in low:
            return get_joke()

        # --- перевод ---
        m = re.match(r"переведи\s+(.+?)(?:\s+на\s+(\w+))?$", low)
        if m:
            lang = m.group(2) or "en"
            lang = "en" if lang.startswith("англ") else "ru"
            return translate(m.group(1), lang)

        # --- помощь по коду ---
        if re.search(r"(что не так|почему ошибка|разбери ошибку|в чём ошибка)", low):
            return self.code_helper.explain_error()
        m = re.match(r"(?:объясни|разбери)\s+(?:файл|код)\s+(.+)", low)
        if m:
            return self.code_helper.explain_code(m.group(1).strip())
        m = re.match(r"(?:найди|проверь)\s+баг\w*\s+(?:в\s+)?(.+)", low)
        if m:
            return self.code_helper.find_bugs(m.group(1).strip())

        # --- пользовательские команды из commands.json ---
        for section in COMMANDS.values():
            if not isinstance(section, dict):
                continue
            for phrase in section.get("phrases", []):
                if phrase.lower() in low:
                    results = []
                    for action in section.get("actions", []):
                        if action.get("target"):  # пропускаем пустые заготовки
                            results.append(self.executor.run(action))
                    return " ".join(results) or "Команда выполнена."

        # --- таймер помодор ---
        m = re.search(r"(помидор|помодор|таймер)\s*(?:на\s*)?(\d+)?", low)
        if m:
            minutes = int(m.group(2) or 25)
            import threading
            def ring():
                msg = f"Сэр, {minutes} минут истекли. Таймер сработал."
                self.speaker.say(msg)
                if self.telegram:
                    self.telegram.send(msg)
            threading.Timer(minutes * 60, ring).start()
            return f"Таймер на {minutes} минут запущен. Работаем, сэр."

        # --- стоп/тишина ---
        if low in ("тишина", "молчи", "стоп", "замолчи"):
            return "..."

        # --- всё остальное → мозг Gemini ---
        answer = self.brain.ask(text)
        return answer or ("Мозг не подключён, сэр. Вставьте ключ Gemini в config.json, "
                          "и я стану гением.")
