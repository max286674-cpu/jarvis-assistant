"""Новости дня: важные сводки из бесплатных RSS-лент."""
import feedparser

FEEDS = {
    "world": [
        ("Lenta", "https://lenta.ru/rss/news"),
        ("РИА", "https://ria.ru/export/rss2/archive/index.xml"),
    ],
    "belarus": [
        ("БЕЛТА", "https://www.belta.by/rss"),
        ("TUT", "https://news.tut.by/rss/index.rss"),
    ],
    "tech": [
        ("Хабр ИИ", "https://habr.com/ru/rss/hubs/ai/?fl=ru"),
        ("Хабр", "https://habr.com/ru/rss/news/?fl=ru"),
    ],
    "crypto": [
        ("Cointelegraph RU", "https://ru.cointelegraph.com/rss"),
        ("Cointelegraph", "https://cointelegraph.com/rss"),
    ],
}

CATEGORY_NAMES = {
    "world": "Мировые новости",
    "belarus": "Новости Беларуси",
    "tech": "Технологии и ИИ",
    "crypto": "Крипторынок",
}


def _headlines(category: str, limit: int = 5) -> list[str]:
    items = []
    for name, url in FEEDS.get(category, []):
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                title = (entry.get("title") or "").strip()
                if title and len(title) > 15:
                    items.append(title)
            if len(items) >= limit:
                break
        except Exception:
            continue
    return items[:limit]


def get_news(category: str = "world") -> str:
    """Возвращает голосовую сводку по категории."""
    titles = _headlines(category)
    if not titles:
        return "Новостные каналы молчат, сэр. Возможно, мир решил взять паузу."
    label = CATEGORY_NAMES.get(category, "Сводка")
    return f"{label}, сэр: " + "; ".join(titles)


def day_digest() -> str:
    """Краткая сводка дня: топ по всем категориям."""
    parts = []
    for cat in ("world", "belarus", "tech", "crypto"):
        titles = _headlines(cat, limit=2)
        if titles:
            parts.append(f"{CATEGORY_NAMES[cat]}: " + "; ".join(titles))
    if not parts:
        return ""
    return " Важное за сутки: " + " | ".join(parts)
