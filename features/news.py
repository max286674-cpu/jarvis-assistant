"""Новости дня: RSS-сводки с таймаутом и коротким кэшем."""
import time
import feedparser
import requests

FEEDS={
    "world":[("Lenta","https://lenta.ru/rss/news"),("РИА","https://ria.ru/export/rss2/archive/index.xml")],
    "belarus":[("БЕЛТА","https://www.belta.by/rss"),("Беларусь","https://www.belarus.by/ru/press-center/rss")],
    "tech":[("Хабр ИИ","https://habr.com/ru/rss/hubs/ai/?fl=ru"),("Хабр","https://habr.com/ru/rss/news/?fl=ru")],
    "crypto":[("Cointelegraph RU","https://ru.cointelegraph.com/rss"),("Cointelegraph","https://cointelegraph.com/rss")],
}
CATEGORY_NAMES={"world":"Мировые новости","belarus":"Новости Беларуси","tech":"Технологии и ИИ","crypto":"Крипторынок"}
_cache={}

def _headlines(category: str, limit: int=5):
    key=(category,limit); cached=_cache.get(key)
    if cached and time.time()-cached[0]<300: return cached[1]
    items=[]
    for name,url in FEEDS.get(category,[]):
        try:
            r=requests.get(url,headers={"User-Agent":"Jarvis/1.0"},timeout=7); r.raise_for_status()
            feed=feedparser.parse(r.content)
            for entry in feed.entries[:limit]:
                title=" ".join((entry.get("title") or "").split())
                if title and len(title)>15: items.append(title)
            if len(items)>=limit: break
        except Exception: continue
    result=items[:limit]; _cache[key]=(time.time(),result); return result

def get_news(category: str="world") -> str:
    category=category if category in FEEDS else "world"; titles=_headlines(category)
    if not titles: return "Новостные каналы молчат, сэр."
    return f"{CATEGORY_NAMES[category]}, сэр: "+"; ".join(titles)

def day_digest() -> str:
    parts=[]
    for cat in ("world","belarus","tech","crypto"):
        titles=_headlines(cat,2)
        if titles: parts.append(f"{CATEGORY_NAMES[cat]}: "+"; ".join(titles))
    return " Важное за сутки: "+" | ".join(parts) if parts else ""
