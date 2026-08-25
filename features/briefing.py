"""Брифинг: погода, курсы валют, состояние системы, время."""
import datetime
import urllib.request
import json as jsonlib


def _fetch(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_weather(city: str = "Moscow") -> str:
    try:
        raw = _fetch(f"https://wttr.in/{city}?format=j1&lang=ru")
        data = jsonlib.loads(raw)
        cur = data["current_condition"][0]
        desc = cur.get("lang_ru", [{"value": cur["weatherDesc"][0]["value"]}])[0]["value"]
        return f"За окном {desc}, {cur['temp_C']}°, ощущается как {cur['FeelsLikeC']}°."
    except Exception:
        return "Метеослужба молчит, сэр."


def get_currency() -> str:
    try:
        raw = _fetch("https://www.cbr-xml-daily.ru/daily_json.js")
        data = jsonlib.loads(raw)
        d = data["Valute"]
        return (f"Доллар {d['USD']['Value']:.2f}, евро {d['EUR']['Value']:.2f} рубля. "
                f"Курс стабильно нестабильный.")
    except Exception:
        return "Центробанк не отвечает, сэр."


def get_system_stats() -> str:
    try:
        import psutil, platform
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        bat = ""
        if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
            bat = f", заряд {psutil.sensors_battery().percent}%"
        mood = "дышит ровно" if cpu < 60 else "потеет"
        return (f"Система {mood}: процессор {cpu}%, память {ram}%{bat}. "
                f"Ось {platform.release()}, время {datetime.datetime.now().strftime('%H:%M')}.")
    except Exception as e:
        return f"Диагностика не удалась: {e}"


def full_briefing(tasks_text: str = "", tenders=None) -> str:
    parts = []
    hour = datetime.datetime.now().hour
    if hour < 6:
        greet = "Доброй ночи, сэр."
    elif hour < 12:
        greet = "Доброе утро, сэр."
    elif hour < 18:
        greet = "Добрый день, сэр."
    else:
        greet = "Добрый вечер, сэр."
    parts.append(greet)
    parts.append(get_weather())
    parts.append(get_currency())
    if tasks_text:
        parts.append(tasks_text)
    try:
        from features.news import day_digest
        digest = day_digest()
        if digest:
            parts.append(digest)
    except Exception:
        pass
    if tenders is not None:
        try:
            t = tenders.daily_check()
            if t:
                parts.append(t)
        except Exception:
            pass
    return " ".join(parts)


def get_joke() -> str:
    jokes = [
        "Программист ставит на ночь два стакана: один с водой — попить, второй пустой — не попить.",
        "Сэр, я бы рассказал шутку про UDP... но не уверен, что она до вас дойдёт.",
        "Лучший способ ускорить компьютер — уронить его с девятого этажа. Полёт всегда быстрый.",
        "Дедлайн — это когда «почти готово» превращается в «было почти готово».",
        "Мой любимый вид отдыха — как ваш режим работы: теоретически существует.",
    ]
    import random
    return random.choice(jokes)


def translate(text: str, target_lang: str = "en") -> str:
    """Простой перевод через MyMemory API (бесплатный)."""
    try:
        pair = "ru|en" if target_lang == "en" else "en|ru"
        raw = _fetch(f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair={pair}")
        data = jsonlib.loads(raw)
        return data["responseData"]["translatedText"]
    except Exception:
        return "Переводческий модуль споткнулся, сэр."


import urllib.parse  # noqa: E402 (для translate)


def get_crypto() -> str:
    """Курсы крипты через CoinGecko (бесплатно, без ключей)."""
    try:
        raw = _fetch(
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin,ethereum,toncoin&vs_currencies=usd&include_24hr_change=true"
        )
        data = jsonlib.loads(raw)
        names = {"bitcoin": "Биткоин", "ethereum": "Эфир", "toncoin": "TON"}
        parts = []
        for key, name in names.items():
            if key in data:
                d = data[key]
                ch = d.get("usd_24h_change", 0) or 0
                arrow = "вырос на" if ch >= 0 else "упал на"
                parts.append(f"{name} ${d['usd']:,.0f} ({arrow} {abs(ch):.1f}% за сутки)")
        return "Рынок, сэр: " + "; ".join(parts) + "."
    except Exception:
        return "Биржи молчат, сэр. Видимо, рынок тоже решил отдохнуть."
