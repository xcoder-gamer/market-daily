"""Pure-Python technical indicators. All inputs are lists of floats, oldest first."""
from __future__ import annotations

import math
from typing import Sequence

# trading-day lookbacks
PERIODS = {"1d": 1, "1w": 5, "1m": 21, "6m": 126, "1y": 252}


def sma(values: Sequence[float], n: int) -> float | None:
    if n <= 0 or len(values) < n:
        return None
    return sum(values[-n:]) / n


def sma_series(values: Sequence[float], n: int) -> list[float | None]:
    out: list[float | None] = []
    run = 0.0
    for i, v in enumerate(values):
        run += v
        if i >= n:
            run -= values[i - n]
        out.append(run / n if i >= n - 1 else None)
    return out


def rsi(values: Sequence[float], n: int = 14) -> float | None:
    """Wilder's RSI. Needs n+1 closes."""
    if len(values) < n + 1:
        return None
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_g = sum(gains[:n]) / n
    avg_l = sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        avg_g = (avg_g * (n - 1) + g) / n
        avg_l = (avg_l * (n - 1) + l) / n
    if avg_l == 0:
        return 100.0 if avg_g > 0 else 50.0
    rs = avg_g / avg_l
    return 100.0 - 100.0 / (1.0 + rs)


def pct_change(values: Sequence[float], lookback: int) -> float | None:
    if lookback <= 0 or len(values) <= lookback or values[-1 - lookback] == 0:
        return None
    return (values[-1] / values[-1 - lookback] - 1.0) * 100.0


def volatility(values: Sequence[float], n: int = 20) -> dict | None:
    """Simple volatility: stdev of the last n daily % returns, plus annualised (x sqrt 252)."""
    if len(values) < n + 1:
        return None
    rets = [(values[i] / values[i - 1] - 1.0) * 100.0 for i in range(len(values) - n, len(values))]
    mean = sum(rets) / n
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (n - 1))
    return {"daily_pct": sd, "annual_pct": sd * math.sqrt(252)}


def high_low(highs: Sequence[float], lows: Sequence[float], n: int = 252) -> tuple[float, float]:
    return max(highs[-n:]), min(lows[-n:])


def range_position(close: float, low: float, high: float) -> float:
    """0 = at the 52-week low, 100 = at the 52-week high."""
    return 50.0 if high == low else (close - low) / (high - low) * 100.0


def compute_metrics(candles: Sequence[dict]) -> dict:
    """candles: ascending [{'d','o','h','l','c'}]. Returns the full metric set used by the site."""
    closes = [c["c"] for c in candles]
    highs = [c.get("h", c["c"]) for c in candles]
    lows = [c.get("l", c["c"]) for c in candles]
    if len(closes) < 2:
        raise ValueError("need at least 2 candles")
    last = closes[-1]
    m: dict = {
        "date": candles[-1]["d"],
        "last": last,
        "prev_close": closes[-2],
        "change": last - closes[-2],
        "change_pct": pct_change(closes, 1),
        "changes": {k: pct_change(closes, n) for k, n in PERIODS.items()},
        "ma": {str(n): sma(closes, n) for n in (20, 50, 200)},
        "rsi14": rsi(closes, 14),
        "vol": volatility(closes, 20),
        "candles_available": len(closes),
    }
    hi, lo = high_low(highs, lows, 252)
    m["high52"], m["low52"] = hi, lo
    m["from_high_pct"] = (last / hi - 1.0) * 100.0
    m["from_low_pct"] = (last / lo - 1.0) * 100.0
    m["range_pos"] = range_position(last, lo, hi)
    m["range_is_partial"] = len(closes) < 252
    return m


def find_similar_level(candles: Sequence[dict], tolerance_pct: float = 0.5, min_gap_days: int = 20) -> dict | None:
    """Most recent earlier date whose close was within +/- tolerance of today's close,
    skipping the last `min_gap_days` sessions so it is a genuinely earlier visit."""
    if len(candles) <= min_gap_days + 1:
        return None
    last = candles[-1]["c"]
    for c in reversed(candles[: -min_gap_days]):
        if abs(c["c"] / last - 1.0) * 100.0 <= tolerance_pct:
            return {"date": c["d"], "close": c["c"]}
    return None
