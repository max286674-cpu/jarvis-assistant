"""Загрузка настроек и безопасные runtime-пути."""
import json
import os
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parent.parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
BASE_DIR = BUNDLE_DIR

# В однофайловом EXE bundle read-only, поэтому БД/кэш/логи храним в AppData.
if getattr(sys, "frozen", False):
    DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "Jarvis" / "data"
else:
    DATA_DIR = SOURCE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _load(name: str) -> dict:
    path = BASE_DIR / name
    if not path.exists(): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_json(name: str, data: dict) -> None:
    path = BASE_DIR / name
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

CONFIG = _load("config.json")
COMMANDS = _load("commands.json")

def data_file(name: str) -> Path:
    return DATA_DIR / name
