"""Крипто-сторож: следит за ценой и алертит голосом + в Telegram."""
import json
import threading
import time
import urllib.request

from core.config import data_file

WATCH_FILE = "crypto_watch.json"
COINS = {
    "биткоин": "bitcoin", "bitcoin": "bitcoin", "бтс": "bitcoin",
    "эфир": "ethereum", "эфириум": "ethereum", "ethereum": "ethereum",
    "тон": "the-open-network", "ton": "the-open-network",
    "солана": "solana", "solana": "solana",
}


_price_cache: dict[str, tuple[float, float]] = {}  # coin_id -> (цена, время)


def _price(coin_id: str, max_retries: int = 3) -> float | None:
    """Цена с кэшем (60с) и ретраями — переживаем rate-limit CoinGecko."""
    import time as _t
    now = _t.time()
    cached = _price_cache.get(coin_id)
    if cached and now - cached[1] < 60:
        return cached[0]
    delay = 2
    for attempt in range(max_retries):
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                price = float(json.loads(r.read())[coin_id]["usd"])
            _price_cache[coin_id] = (price, now)
            return price
        except Exception:
            if attempt < max_retries - 1:
                _t.sleep(delay)
                delay *= 2
    # фолбэк: Binance (без лимитов для простых запросов)
    symbol_map = {
        "bitcoin": "BTCUSDT", "ethereum": "ETHUSDT",
        "solana": "SOLUSDT", "the-open-network": "TONUSDT",
    }
    sym = symbol_map.get(coin_id)
    if sym:
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={sym}"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                price = float(json.loads(r.read())["price"])
            _price_cache[coin_id] = (price, now)
            return price
        except Exception:
            pass
    # последнее известное значение лучше, чем ничего
    return cached[0] if cached else None


class CryptoWatch:
    def __init__(self, speaker, telegram=None):
        self.speaker = speaker
        self.telegram = telegram
        self.path = data_file(WATCH_FILE)
        threading.Thread(target=self._loop, daemon=True).start()

    def _load(self) -> list:
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self, items):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    def add(self, text: str) -> str:
        """Парсит: 'следи за биткоином если упадёт ниже 70000'."""
        low = text.lower()
        coin_key = next((k for k in COINS if k in low), None)
        if not coin_key:
            return ("Сэр, уточните монету: биткоин, эфир, ton или solana. "
                    "Формат: «следи за биткоином, если упадёт ниже 70000».")
        import re
        m = re.search(r"(ниже|меньше|выше|больше)\s*([\d\s.,kк]+)", low)
        if not m:
            return "Укажите порог, сэр: «...если упадёт ниже 70000»."
        direction = "below" if m.group(1) in ("ниже", "меньше") else "above"
        raw = m.group(2).replace(" ", "").replace(",", ".").lower()
        threshold = float(raw.replace("k", "")) * (1000 if "k" in raw else 1)

        items = self._load()
        items.append({
            "coin_id": COINS[coin_key], "coin_name": coin_key,
            "direction": direction, "threshold": threshold,
        })
        self._save(items)
        word = "ниже" if direction == "below" else "выше"
        cur = _price(COINS[coin_key])
        cur_txt = f" Текущая цена ${cur:,.0f}." if cur else ""
        return (f"Принято, сэр. Ставлю наблюдение: {coin_key}, "
                f"сигнал при цене {word} ${threshold:,.0f}.{cur_txt}")

    def list_watches(self) -> str:
        items = self._load()
        if not items:
            return "Активных наблюдений нет, сэр."
        lines = []
        for w in items:
            word = "ниже" if w["direction"] == "below" else "выше"
            lines.append(f"{w['coin_name']} {word} ${w['threshold']:,.0f}")
        return "Слежу за: " + "; ".join(lines) + "."

    def clear(self) -> str:
        self._save([])
        return "Все наблюдения сняты, сэр."

    def check_once(self) -> list[str]:
        """Одна проверка всех условий. Возвращает сообщения о срабатываниях."""
        items = self._load()
        fired, keep = [], []
        for w in items:
            price = _price(w["coin_id"])
            if price is None:
                keep.append(w)
                continue
            hit = (w["direction"] == "below" and price <= w["threshold"]) or (
                w["direction"] == "above" and price >= w["threshold"]
            )
            if hit:
                word = "упал до" if w["direction"] == "below" else "вырос до"
                fired.append(
                    f"Сэр, внимание: {w['coin_name']} {word} ${price:,.0f} "
                    f"— порог ${w['threshold']:,.0f} пройден."
                )
            else:
                keep.append(w)
        if fired:
            self._save(keep)
        return fired

    def _loop(self):
        while True:
            try:
                for msg in self.check_once():
                    self.speaker.say(msg)
                    if self.telegram:
                        self.telegram.send(msg)
            except Exception:
                pass
            time.sleep(300)  # проверка раз в 5 минут
