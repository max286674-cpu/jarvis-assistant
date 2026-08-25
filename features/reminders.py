"""Напоминания и задачи. Живут в JSON, переживают перезапуск."""
import json
import re
import threading
import time
from datetime import datetime

from core.config import data_file

REMINDERS_FILE = "reminders.json"
TASKS_FILE = "tasks.json"


def _load(path) -> list:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ReminderEngine:
    def __init__(self, speaker, telegram=None):
        self.speaker = speaker
        self.telegram = telegram
        self.reminders_path = data_file(REMINDERS_FILE)
        self.tasks_path = data_file(TASKS_FILE)
        threading.Thread(target=self._loop, daemon=True).start()

    # ---------- напоминания ----------
    def add_reminder(self, text: str, when_ts: float) -> str:
        items = _load(self.reminders_path)
        items.append({"text": text, "ts": when_ts})
        _save(self.reminders_path, items)
        t = datetime.fromtimestamp(when_ts).strftime("%H:%M")
        return f"Напоминание «{text}» поставлено на {t}."

    def parse_and_add(self, text: str) -> str:
        """Парсит фразы вида: 'напомни через час позвонить маме',
        'напомни в 19:00 ...', 'напомни через 10 минут ...'."""
        low = text.lower()
        body = re.sub(r"^.*?(напомни\S*)\s*", "", low).strip()
        now = time.time()

        m = re.search(r"через\s+(\d+)\s*(сек|мин|час)", low)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            delay = n * (1 if unit.startswith("сек") else 60 if unit.startswith("мин") else 3600)
            task = re.sub(r".*?через\s+\d+\s*\w+\s*", "", body).strip() or "напоминание"
            return self.add_reminder(task, now + delay)

        m = re.search(r"в\s+(\d{1,2})[:.](\d{2})", low)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            target = datetime.now().replace(hour=hh, minute=mm, second=0)
            if target.timestamp() < now:
                target = target.fromtimestamp(target.timestamp() + 86400)
            task = re.sub(r".*?в\s+\d{1,2}[:.]\d{2}\s*", "", body).strip() or "напоминание"
            return self.add_reminder(task, target.timestamp())

        return "Сэр, уточните время: «напомни через 30 минут ...» или «напомни в 19:00 ...»."

    def due_check(self) -> list:
        """Возвращает и удаляет сработавшие напоминания."""
        items = _load(self.reminders_path)
        due = [r for r in items if r["ts"] <= time.time()]
        if due:
            _save(self.reminders_path, [r for r in items if r["ts"] > time.time()])
        return due

    def _loop(self):
        while True:
            for r in self.due_check():
                msg = f"Сэр, напоминание: {r['text']}."
                self.speaker.say(msg)
                if self.telegram:
                    self.telegram.send(msg)
            time.sleep(20)

    # ---------- задачи ----------
    def add_task(self, text: str) -> str:
        tasks = _load(self.tasks_path)
        clean = re.sub(r"^(добавь задачу|задача|задачу)\s*", "", text.lower()).strip()
        tasks.append({"text": clean, "done": False, "created": time.time()})
        _save(self.tasks_path, tasks)
        return f"Задача добавлена. В списке {len(tasks)} активных."

    def list_tasks(self) -> str:
        tasks = [t for t in _load(self.tasks_path) if not t["done"]]
        if not tasks:
            return "Список пуст, сэр. Редкая роскошь."
        lines = [f"{i+1}. {t['text']}" for i, t in enumerate(tasks[:7])]
        return "Ваши задачи: " + "; ".join(lines)

    def done_task(self, num: int) -> str:
        tasks = _load(self.tasks_path)
        active = [i for i, t in enumerate(tasks) if not t["done"]]
        if 0 < num <= len(active):
            tasks[active[num - 1]]["done"] = True
            _save(self.tasks_path, tasks)
            return f"Задача {num} закрыта. Так держать, сэр."
        return "Не нашёл такой задачи в списке."

    def morning_tasks(self) -> str:
        tasks = [t for t in _load(self.tasks_path) if not t["done"]]
        if not tasks:
            return ""
        return "На сегодня в плане: " + "; ".join(t["text"] for t in tasks[:5]) + "."
