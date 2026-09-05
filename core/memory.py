"""Persistent explicit memory on SQLite + FTS5, with deterministic connection cleanup on Windows."""
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

class MemoryStore:
    def __init__(self,path:Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._init_db()
    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path,timeout=10)
        try: yield db; db.commit()
        finally: db.close()
    def _init_db(self):
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, text TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'fact', created_at TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)")
            try:
                db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text, category, content='memories', content_rowid='id')")
                db.execute("INSERT INTO memories_fts(rowid,text,category) SELECT id,text,category FROM memories WHERE id NOT IN (SELECT rowid FROM memories_fts)")
            except sqlite3.OperationalError: pass
    def add(self,text:str,category:str="fact"):
        text=(text or "").strip(); category=(category or "fact").strip()[:40]
        if not text:return
        now=datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            cur=db.execute("INSERT INTO memories(text,category,created_at) VALUES(?,?,?)",(text,category,now))
            try:db.execute("INSERT INTO memories_fts(rowid,text,category) VALUES(?,?,?)",(cur.lastrowid,text,category))
            except sqlite3.OperationalError:pass
    def search(self,query:str,limit:int=5):
        query=" ".join((query or "").split())
        if not query:return []
        with self._db() as db:
            try:
                safe=" ".join(w.replace('"','') for w in query.split() if len(w)>2)[:300]
                rows=db.execute("SELECT m.text FROM memories_fts f JOIN memories m ON m.id=f.rowid WHERE memories_fts MATCH ? ORDER BY m.id DESC LIMIT ?",(safe,limit)).fetchall()
                if rows:return [r[0] for r in rows]
            except sqlite3.OperationalError:pass
            rows=db.execute("SELECT text FROM memories ORDER BY id DESC LIMIT ?",(limit*4,)).fetchall()
        words=[w.lower() for w in query.split() if len(w)>3]
        scored=sorted(((sum(w in row[0].lower() for w in words),row[0]) for row in rows),reverse=True)
        return [text for score,text in scored if score>0][:limit]
    def clear(self):
        with self._db() as db:
            db.execute("DELETE FROM memories")
            try:db.execute("DELETE FROM memories_fts")
            except sqlite3.OperationalError:pass
