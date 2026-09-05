"""Напоминания и задачи. Надёжное хранение в runtime data."""
import json, re, threading, time
from datetime import datetime, timedelta
from core.config import data_file

REMINDERS_FILE = "reminders.json"
TASKS_FILE = "tasks.json"

def _load(path):
    if not path.exists(): return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError): return []

def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

class ReminderEngine:
    def __init__(self, speaker, telegram=None):
        self.speaker, self.telegram = speaker, telegram
        self.reminders_path, self.tasks_path = data_file(REMINDERS_FILE), data_file(TASKS_FILE)
        self._lock = threading.RLock()
        threading.Thread(target=self._loop, daemon=True, name="reminders").start()

    def add_reminder(self, text: str, when_ts: float) -> str:
        text = (text or "напоминание").strip()[:500]
        with self._lock:
            items = _load(self.reminders_path)
            items.append({"text": text, "ts": float(when_ts), "created": time.time()})
            _save(self.reminders_path, items)
        dt = datetime.fromtimestamp(when_ts)
        return f"Напоминание «{text}» поставлено на {dt:%d.%m в %H:%M}."

    def parse_and_add(self, text: str) -> str:
        low = (text or "").lower().strip()
        body = re.sub(r"^.*?напомни(?:\s+мне)?\s*", "", low).strip()
        now = datetime.now()
        m = re.search(r"через\s+(\d+)\s*(секунд?а?|сек|минут?ы?|мин|час(?:а|ов)?)", low)
        if m:
            n = int(m.group(1)); unit = m.group(2)
            seconds = n if unit.startswith("сек") else n * 60 if unit.startswith("мин") else n * 3600
            task = re.sub(r".*?через\s+\d+\s*\w+\s*", "", body).strip() or "напоминание"
            return self.add_reminder(task, time.time() + seconds)
        m = re.search(r"в\s+(\d{1,2})[:.](\d{2})", low)
        if m:
            hh, mm = int(m.group(1)), int(m.group(2))
            if hh > 23 or mm > 59: return "Сэр, время указано некорректно."
            target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if target <= now: target += timedelta(days=1)
            task = re.sub(r".*?в\s+\d{1,2}[:.]\d{2}\s*", "", body).strip() or "напоминание"
            return self.add_reminder(task, target.timestamp())
        return "Сэр, уточните время: «напомни через 30 минут ...» или «напомни в 19:00 ...»."

    def due_check(self):
        now = time.time()
        with self._lock:
            items = _load(self.reminders_path)
            due = [r for r in items if float(r.get("ts", 0)) <= now]
            if due: _save(self.reminders_path, [r for r in items if float(r.get("ts", 0)) > now])
            return due

    def _loop(self):
        while True:
            try:
                for r in self.due_check():
                    msg = f"Сэр, напоминание: {r.get('text', 'напоминание')}."
                    self.speaker.say(msg)
                    if self.telegram: self.telegram.send(msg)
            except Exception as e: print(f"[reminders: {e}]")
            time.sleep(10)

    def add_task(self, text: str) -> str:
        clean = re.sub(r"^(добавь задачу|задача|задачу)\s*", "", (text or "").strip(), flags=re.I).strip()[:500]
        if not clean: return "Назовите задачу, сэр."
        with self._lock:
            tasks = _load(self.tasks_path)
            tasks.append({"text": clean, "done": False, "created": time.time()})
            _save(self.tasks_path, tasks)
            active = sum(not bool(t.get("done")) for t in tasks)
        return f"Задача добавлена. Активных задач: {active}."

    def list_tasks(self) -> str:
        tasks = [t for t in _load(self.tasks_path) if not t.get("done")]
        if not tasks: return "Список пуст, сэр. Редкая роскошь."
        return "Ваши задачи: " + "; ".join(f"{i+1}. {t.get('text','')}" for i, t in enumerate(tasks[:10]))

    def done_task(self, num: int) -> str:
        try: num = int(num)
        except (TypeError, ValueError): return "Укажите номер задачи."
        with self._lock:
            tasks = _load(self.tasks_path); active = [i for i,t in enumerate(tasks) if not t.get("done")]
            if not 0 < num <= len(active): return "Не нашёл такую задачу в списке."
            tasks[active[num-1]]["done"] = True; tasks[active[num-1]]["completed"] = time.time(); _save(self.tasks_path, tasks)
        return f"Задача {num} закрыта. Так держать, сэр."

    def morning_tasks(self) -> str:
        tasks = [t for t in _load(self.tasks_path) if not t.get("done")]
        return "На сегодня в плане: " + "; ".join(t.get("text","") for t in tasks[:5]) + "." if tasks else ""
