"""Trading-day check: skips weekends and NSE holidays from data/holidays.json."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))  # India has no DST; avoids a tzdata dependency


def today_ist() -> dt.date:
    return dt.datetime.now(IST).date()


def load_holidays(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def is_trading_day(day: dt.date, holidays: dict[str, str]) -> bool:
    return day.weekday() < 5 and day.isoformat() not in holidays


def skip_reason(day: dt.date, holidays: dict[str, str]) -> str | None:
    if day.weekday() >= 5:
        return "weekend"
    return holidays.get(day.isoformat())
