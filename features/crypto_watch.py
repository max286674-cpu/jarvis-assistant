"""Крипто-сторож: устойчивые ценовые алерты с голосом и Telegram."""
import json, re, threading, time, urllib.request
from core.config import data_file

WATCH_FILE = "crypto_watch.json"
COINS = {"биткоин":"bitcoin","bitcoin":"bitcoin","бтс":"bitcoin","эфир":"ethereum","эфириум":"ethereum","ethereum":"ethereum","тон":"the-open-network","ton":"the-open-network","солана":"solana","solana":"solana"}
_price_cache = {}

def _price(coin_id: str, max_retries: int = 2):
    now = time.time(); cached = _price_cache.get(coin_id)
    if cached and now - cached[1] < 60: return cached[0]
    urls = [f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"]
    symbol = {"bitcoin":"BTCUSDT","ethereum":"ETHUSDT","solana":"SOLUSDT","the-open-network":"TONUSDT"}.get(coin_id)
    if symbol: urls.append(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
    for url in urls:
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent":"Jarvis/1.0"})
                with urllib.request.urlopen(req, timeout=8) as r: data = json.loads(r.read())
                price = float(data[coin_id]["usd"] if "coingecko" in url else data["price"])
                _price_cache[coin_id] = (price, now); return price
            except Exception:
                if attempt + 1 < max_retries: time.sleep(1.5)
    return cached[0] if cached else None

class CryptoWatch:
    def __init__(self, speaker, telegram=None):
        self.speaker, self.telegram = speaker, telegram
        self.path = data_file(WATCH_FILE)
        self._lock = threading.RLock()
        threading.Thread(target=self._loop, daemon=True, name="crypto-watch").start()

    def _load(self):
        if not self.path.exists(): return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8")); return data if isinstance(data,list) else []
        except (OSError,json.JSONDecodeError): return []

    def _save(self, items):
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(self.path)

    def add(self, text: str) -> str:
        low=(text or "").lower(); coin_key=next((k for k in COINS if k in low),None)
        if not coin_key: return "Сэр, уточните монету: биткоин, эфир, TON или Solana."
        m=re.search(r"(ниже|меньше|выше|больше)\s*([\d\s.,]+)\s*([kк]?)",low)
        if not m: return "Укажите порог: «следи за биткоином, если упадёт ниже 70000»."
        raw=m.group(2).replace(" ","").replace(",","."); threshold=float(raw)*(1000 if m.group(3) else 1)
        direction="below" if m.group(1) in ("ниже","меньше") else "above"; coin_id=COINS[coin_key]
        with self._lock:
            items=self._load()
            if not any(w.get("coin_id")==coin_id and w.get("direction")==direction and float(w.get("threshold",-1))==threshold for w in items):
                items.append({"coin_id":coin_id,"coin_name":coin_key,"direction":direction,"threshold":threshold}); self._save(items)
        cur=_price(coin_id); cur_txt=f" Текущая цена ${cur:,.0f}." if cur else ""
        word="ниже" if direction=="below" else "выше"
        return f"Принято, сэр. Слежу за {coin_key}: сигнал {word} ${threshold:,.0f}.{cur_txt}"

    def list_watches(self) -> str:
        items=self._load()
        if not items: return "Активных наблюдений нет, сэр."
        return "Слежу за: " + "; ".join(f"{w.get('coin_name')} {'ниже' if w.get('direction')=='below' else 'выше'} ${float(w.get('threshold',0)):,.0f}" for w in items) + "."

    def clear(self) -> str:
        with self._lock: self._save([])
        return "Все наблюдения сняты, сэр."

    def check_once(self):
        with self._lock: items=self._load()
        fired=[]; keep=[]
        for w in items:
            price=_price(w.get("coin_id"))
            if price is None: keep.append(w); continue
            hit=(w.get("direction")=="below" and price<=float(w.get("threshold",0))) or (w.get("direction")=="above" and price>=float(w.get("threshold",0)))
            if hit:
                word="упал до" if w.get("direction")=="below" else "вырос до"
                fired.append(f"Сэр, внимание: {w.get('coin_name')} {word} ${price:,.0f} — порог ${float(w.get('threshold',0)):,.0f} пройден.")
            else: keep.append(w)
        if len(keep)!=len(items):
            with self._lock: self._save(keep)
        return fired

    def _loop(self):
        while True:
            try:
                for msg in self.check_once():
                    self.speaker.say(msg)
                    if self.telegram: self.telegram.send(msg)
            except Exception as e: print(f"[crypto-watch: {e}]")
            time.sleep(300)
