"""Загрузка и сохранение настроек Джарвиса."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load(name: str) -> dict:
    path = BASE_DIR / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(name: str, data: dict) -> None:
    path = BASE_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


CONFIG = _load("config.json")
COMMANDS = _load("commands.json")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def data_file(name: str) -> Path:
    return DATA_DIR / name
