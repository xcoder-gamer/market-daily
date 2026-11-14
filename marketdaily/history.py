"""Persistent history: merged daily-candle series per index + one snapshot file per trading day.
Writes are atomic and empty data is never written over existing data."""
from __future__ import annotations

import datetime as dt

from . import config


class EmptyDataError(Exception):
    pass


def is_valid_market_data(data: dict | None) -> bool:
    """NIFTY 50 must be present with a usable history; everything else is optional."""
    if not data:
        return False
    nifty = (data.get("indices") or {}).get("nifty50")
    if not nifty:
        return False
    candles = nifty.get("candles") or []
    return len(candles) >= 30 and candles[-1].get("c", 0) > 0


def merge_candles(settings: config.Settings, key: str, candles: list[dict]) -> list[dict]:
    if not candles:
        raise EmptyDataError(f"no candles for {key}")
    path = settings.candles_dir / f"{key}.json"
    existing = config.read_json(path, []) or []
    by_date = {c["d"]: c for c in existing}
    by_date.update({c["d"]: c for c in candles})  # fresh data wins
    merged = [by_date[d] for d in sorted(by_date)]
    cutoff = (dt.date.fromisoformat(merged[-1]["d"]) - dt.timedelta(days=config.CANDLE_KEEP_DAYS)).isoformat()
    merged = [c for c in merged if c["d"] >= cutoff]
    config.write_json(path, merged)
    return merged


def load_series(settings: config.Settings, key: str, upto: str | None = None) -> list[dict]:
    s = config.read_json(settings.candles_dir / f"{key}.json", []) or []
    return [c for c in s if upto is None or c["d"] <= upto]


def save_snapshot(settings: config.Settings, date: str, snapshot: dict) -> None:
    if not snapshot.get("indices"):
        raise EmptyDataError("refusing to write an empty snapshot")
    config.write_json(settings.history_dir / f"{date}.json", snapshot)


def list_snapshot_dates(settings: config.Settings) -> list[str]:
    if not settings.history_dir.exists():
        return []
    return sorted(p.stem for p in settings.history_dir.glob("*.json"))


def save_data_json(settings: config.Settings, payload: dict) -> bool:
    """Write the public data.json unless the payload is empty. Returns True if written."""
    if not payload.get("indices"):
        print("WARN: refusing to overwrite data.json with empty data")
        return False
    config.write_json(settings.data_json, payload)
    return True
