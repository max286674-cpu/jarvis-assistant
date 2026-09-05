"""Тендерный радар Беларуси: поиск и дедупликация результатов."""
import json, re, urllib.parse, urllib.request
from core.config import data_file

STATE_FILE="tenders_state.json"
KEYWORDS_DEFAULT=["it","разработка","программ","сайт","нейрон"]

def _fetch(url: str) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/1.0","Accept-Language":"ru,en"})
    with urllib.request.urlopen(req,timeout=12) as r: return r.read().decode("utf-8",errors="ignore")

def search_goszakupki(keyword: str, limit: int=5) -> list[dict]:
    results=[]
    try:
        html=_fetch("https://www.goszakupki.by/tenders?search="+urllib.parse.quote(keyword))
        titles=re.findall(r'<a[^>]+href=["\'](/tenders/\d+[^"\']*)["\'][^>]*>([^<]{10,240})</a>',html,re.I)
        seen=set()
        for href,title in titles:
            title=" ".join(title.split())
            if title.lower() in seen: continue
            seen.add(title.lower()); results.append({"title":title,"url":"https://www.goszakupki.by"+href})
            if len(results)>=limit: break
    except Exception as e: print(f"[tenders: {e}]")
    return results

class TenderRadar:
    def __init__(self,speaker,telegram=None):
        self.speaker,self.telegram=speaker,telegram; self.path=data_file(STATE_FILE)
        state=self._load(); self.keywords=state.get("keywords",KEYWORDS_DEFAULT.copy()); self.seen=set(state.get("seen",[]))

    def _load(self):
        try:
            data=json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            return data if isinstance(data,dict) else {}
        except (OSError,json.JSONDecodeError): return {}

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix(".tmp")
        data={"keywords":self.keywords,"seen":list(self.seen)[-500:]}
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(self.path)

    def set_keywords(self,text: str) -> str:
        low=(text or "").lower().strip(); m=re.search(r"(?:по|на тему)\s+(.+)$",low)
        source=m.group(1) if m else low
        words=[w.strip() for w in source.split(",") if len(w.strip())>2][:7]
        if not words: return "Назовите ключевые слова через запятую, сэр."
        self.keywords=words; self._save()
        return "Тендерный радар перенастроен. Слежу за: "+", ".join(words)+"."

    def daily_check(self) -> str:
        found=[]
        for kw in self.keywords[:4]: found.extend(search_goszakupki(kw,limit=3))
        uniq=[]; local=set()
        for item in found:
            key=item["url"]
            if key not in local: local.add(key); uniq.append(item)
        new=[x for x in uniq if x["url"] not in self.seen]
        for x in uniq: self.seen.add(x["url"])
        self._save()
        if not new: return "Новых совпадений по тендерному радару не найдено."
        lines=[f"«{x['title'][:80]}»" for x in new[:5]]
        return f"Тендерный радар, сэр: новых совпадений {len(new)}. "+"; ".join(lines)+"."
