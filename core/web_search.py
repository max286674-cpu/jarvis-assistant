"""Минимальный веб-поиск без API-ключа для агента Jarvis."""
from __future__ import annotations
import html, re
import requests
from urllib.parse import quote_plus

def search_web(query: str, limit: int = 6) -> str:
    query = (query or "").strip()
    if not query: return "Пустой поисковый запрос."
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0 (Jarvis Assistant)"}, timeout=(5, 12))
    r.raise_for_status()
    results = []
    pattern = r'<div class="result results_links results_links_deep web-result ".*?</div>\s*</div>'
    for block in re.findall(pattern, r.text, re.S)[:limit]:
        title = re.search(r'class="result__a"[^>]*>(.*?)</a>', block, re.S)
        snippet = re.search(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', block, re.S)
        href = re.search(r'class="result__a" href="([^"]+)"', block)
        if title:
            clean = lambda s: re.sub(r'<[^>]+>', '', html.unescape(s or '')).strip()
            results.append(f"- {clean(title.group(1))}\n  {clean(snippet.group(1) if snippet else '')}\n  {href.group(1) if href else ''}")
    return "\n".join(results) if results else "Поиск не вернул результатов."
