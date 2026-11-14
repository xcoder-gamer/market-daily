"""Deterministic synthetic market data so the whole pipeline can run offline (python -m marketdaily.main --mock)."""
from __future__ import annotations

import datetime as dt
import random

from . import config

_START = {"nifty50": 22000.0, "sensex": 72500.0, "banknifty": 48000.0, "niftyit": 35000.0}


def _trading_days(end: dt.date, n: int) -> list[dt.date]:
    days, d = [], end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= dt.timedelta(days=1)
    return days[::-1]


def market_data(end: dt.date, n: int = 520, seed: int = 7) -> dict:
    # end must be a weekday; step back if not
    while end.weekday() >= 5:
        end -= dt.timedelta(days=1)
    rng = random.Random(seed)
    days = _trading_days(end, n)
    indices = {}
    for key, name, _, _ in config.INDICES:
        px, candles = _START[key], []
        for d in days:
            o = px
            px = px * (1 + rng.gauss(0.0004, 0.009))
            hi, lo = max(o, px) * (1 + abs(rng.gauss(0, 0.003))), min(o, px) * (1 - abs(rng.gauss(0, 0.003)))
            candles.append({"d": d.isoformat(), "o": round(o, 2), "h": round(hi, 2), "l": round(lo, 2),
                            "c": round(px, 2), "v": 0.0})
        indices[key] = {"name": name, "candles": candles}
    stocks = []
    for s in config.NIFTY50_DEFAULT:
        prev = rng.uniform(100, 3000)
        chg = rng.gauss(0, 1.6)
        stocks.append({"symbol": s, "last": round(prev * (1 + chg / 100), 2), "prev_close": round(prev, 2),
                       "change_pct": chg})
    commodities = {}
    for key, name, _ in config.COMMODITIES:
        prev = {"gold": 2650.0, "silver": 31.0, "crude": 71.0, "usdinr": 84.2}[key]
        chg = rng.gauss(0, 0.8)
        commodities[key] = {"name": name, "last": round(prev * (1 + chg / 100), 3), "prev_close": prev,
                            "change_pct": chg}
    return {"source": "mock", "indices": indices, "stocks": stocks, "commodities": commodities}


def news(now: dt.datetime) -> list[dict]:
    ts = now.isoformat()
    rows = [
        ("Economic Times", "RBI keeps repo rate unchanged, flags food inflation risk"),
        ("LiveMint", "Foreign investors turn net buyers in Indian equities after three weeks"),
        ("Moneycontrol", "IT firms report mixed deal pipeline as US demand stays cautious"),
        ("Google News", "Crude oil slips as demand worries outweigh supply cuts"),
        ("Economic Times", "Banks report steady credit growth; margins under watch"),
        ("LiveMint", "Rupee edges lower against dollar on importer demand"),
        ("Moneycontrol", "Auto sales data shows festive-season boost for two-wheelers"),
        ("Google News", "Government data: industrial output grows faster than expected"),
    ]
    return [{"title": t, "source": s, "url": f"https://example.com/news/{i}", "published": ts}
            for i, (s, t) in enumerate(rows)]
