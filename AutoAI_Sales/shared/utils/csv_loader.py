from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def data_path(filename: str) -> Path:
    return DATA_DIR / filename


@lru_cache(maxsize=None)
def load_csv(filename: str) -> tuple[dict[str, str], ...]:
    path = data_path(filename)
    if not path.exists():
        return ()
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple({key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle))


def bool_from_str(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def int_from_str(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def list_from_str(value: str | None, delimiter: str = "|") -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]


def text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
