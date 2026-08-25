"""Тендерный радар: новые тендеры Беларуси по ключевым словам."""
import json
import re
import threading
import time
import urllib.request

from core.config import data_file

STATE_FILE = "tenders_state.json"

KEYWORDS_DEFAULT = ["it", "разработка", "программн", "сайт", "нейронн"]


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "ru,en",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="ignore")


def search_goszakupki(keyword: str, limit: int = 5) -> list[dict]:
    """Поиск по goszakupki.by (публичная страница поиска)."""
    results = []
    try:
        html = _fetch(
            f"https://www.goszakupki.by/tenders?search={urllib.parse.quote(keyword)}"
        )
        # заголовки тендеров на странице
        titles = re.findall(r'<a[^>]+href="(/tenders/\d+[^"]*)"[^>]*>([^<]{20,200})</a>', html)
        seen = set()
        for href, title in titles:
            t = title.strip()
            if t in seen:
                continue
            seen.add(t)
            results.append({"title": t, "url": "https://www.goszakupki.by" + href})
            if len(results) >= limit:
                break
    except Exception:
        pass
    return results


class TenderRadar:
    def __init__(self, speaker, telegram=None):
        self.speaker = speaker
        self.telegram = telegram
        self.path = data_file(STATE_FILE)
        self.keywords = KEYWORDS_DEFAULT.copy()

    def set_keywords(self, text: str) -> str:
        """'следи за тендерами по словам разработка, сайт'"""
        low = text.lower()
        m = re.search(r"(?:по|на тему)\s+(.+)$", low)
        words = [w.strip() for w in (m.group(1) if m else low).split(",") if len(w.strip()) > 2]
        if not words:
            return "Назовите ключевые слова через запятую, сэр."
        self.keywords = words[:7]
        return (f"Тендерный радар перенастроен. Слежу за словами: "
                f"{', '.join(self.keywords)}. Утренний брифинг будет пополняться.")

    def daily_check(self) -> str:
        """Ищет свежие тендеры по ключевым словам (для брифинга)."""
        found = []
        for kw in self.keywords[:4]:
            for t in search_goszakupki(kw, limit=2):
                found.append(t)
        if not found:
            return ""
        # убираем дубли по названию
        seen, uniq = set(), []
        for t in found:
            if t["title"] not in seen:
                seen.add(t["title"])
                uniq.append(t)
        self.executor_open = getattr(self, "executor_open", None)
        lines = [f"«{t['title'][:70]}»" for t in uniq[:4]]
        return (f"Тендерный радар, сэр: нашёл {len(uniq)} совпадений. "
                + "; ".join(lines) + ". Скажите «открой тендеры» для сайта.")
