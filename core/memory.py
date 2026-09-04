"""Постоянная память Jarvis на SQLite."""
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

class MemoryStore:
    def __init__(self,path:Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, text TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)")
    def add(self,text:str):
        text=(text or "").strip()
        if text:
            with sqlite3.connect(self.path) as db: db.execute("INSERT INTO memories(text,created_at) VALUES(?,?)",(text,datetime.now(timezone.utc).isoformat()))
    def search(self,query:str,limit:int=5):
        words=[w.lower() for w in query.split() if len(w)>3][:8]
        if not words:return []
        where=" OR ".join(["LOWER(text) LIKE ?"]*len(words)); params=[f"%{w}%" for w in words]
        with sqlite3.connect(self.path) as db: rows=db.execute(f"SELECT text FROM memories WHERE {where} ORDER BY id DESC LIMIT ?",(*params,limit)).fetchall()
        return [r[0] for r in rows]
    def clear(self):
        with sqlite3.connect(self.path) as db: db.execute("DELETE FROM memories")
