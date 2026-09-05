"""Permissioned filesystem tools. Paths are confined to configured roots."""
from __future__ import annotations
from pathlib import Path
import os

class Workspace:
    def __init__(self, roots=None):
        default = [Path.home() / "Desktop", Path.home() / "Documents", Path.home() / "Downloads"]
        self.roots = [Path(p).expanduser().resolve() for p in (roots or default)]

    def _resolve(self, path: str) -> Path:
        p = Path(os.path.expandvars(path)).expanduser().resolve()
        if not any(p == root or root in p.parents for root in self.roots):
            raise PermissionError("Путь находится вне разрешённой рабочей области.")
        return p

    def list_dir(self, path: str = "~"):
        p = self._resolve(path)
        if not p.is_dir(): raise FileNotFoundError(path)
        return [{"name": x.name, "type": "dir" if x.is_dir() else "file"} for x in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:200]]

    def read_text(self, path: str):
        p = self._resolve(path)
        if not p.is_file(): raise FileNotFoundError(path)
        return p.read_text(encoding="utf-8", errors="replace")[:50000]

    def write_text(self, path: str, content: str):
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Файл записан: {p}"

    def delete(self, path: str):
        p = self._resolve(path)
        if p.is_dir(): raise IsADirectoryError("Удаление папок отдельным подтверждаемым инструментом.")
        p.unlink()
        return f"Файл удалён: {p}"
