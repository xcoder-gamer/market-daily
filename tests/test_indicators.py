import math

import pytest

from marketdaily import indicators as ind

WILDER = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
          45.89, 46.03, 45.61, 46.28, 46.28]


def candles(closes, start="2025-01-01"):
    import datetime as dt
    d0 = dt.date.fromisoformat(start)
    return [{"d": (d0 + dt.timedelta(days=i)).isoformat(), "o": c, "h": c * 1.01, "l": c * 0.99, "c": c}
            for i, c in enumerate(closes)]


def test_sma():
    assert ind.sma([1, 2, 3, 4, 5], 5) == 3
    assert ind.sma([1, 2, 3, 4, 5], 2) == 4.5
    assert ind.sma([1, 2], 5) is None


def test_sma_series_matches_sma():
    vals = [float(i * i % 17) for i in range(40)]
    s = ind.sma_series(vals, 5)
    assert s[3] is None and s[4] == pytest.approx(ind.sma(vals[:5], 5))
    assert s[-1] == pytest.approx(ind.sma(vals, 5))


def test_rsi_wilder_reference():
    # first 14-period RSI of the classic Wilder/StockCharts data set
    assert ind.rsi(WILDER, 14) == pytest.approx(70.46, abs=0.1)


def test_rsi_extremes_and_short_input():
    assert ind.rsi(list(range(1, 40)), 14) == 100.0
    assert ind.rsi(list(range(40, 1, -1)), 14) == pytest.approx(0.0)
    assert ind.rsi([1, 2, 3], 14) is None
    assert ind.rsi([5.0] * 30, 14) == 50.0


def test_pct_change():
    assert ind.pct_change([100, 110], 1) == pytest.approx(10.0)
    assert ind.pct_change([100, 100, 100, 150], 3) == pytest.approx(50.0)
    assert ind.pct_change([100], 1) is None


def test_volatility():
    assert ind.volatility([100.0] * 30, 20)["daily_pct"] == 0
    v = ind.volatility([100 * (1.01 if i % 2 else 0.99) ** i for i in range(40)], 20)
    assert v["annual_pct"] == pytest.approx(v["daily_pct"] * math.sqrt(252))
    assert ind.volatility([1, 2], 20) is None


def test_range_position():
    assert ind.range_position(150, 100, 200) == 50
    assert ind.range_position(200, 100, 200) == 100
    assert ind.range_position(5, 5, 5) == 50


def test_compute_metrics_full():
    closes = [100 + i * 0.5 for i in range(300)]
    m = ind.compute_metrics(candles(closes))
    assert m["last"] == closes[-1]
    assert m["change"] == pytest.approx(0.5)
    assert m["ma"]["200"] == pytest.approx(sum(closes[-200:]) / 200)
    assert m["from_high_pct"] < 0 <= m["from_low_pct"]
    assert m["high52"] == pytest.approx(max(c * 1.01 for c in closes[-252:]))
    assert not m["range_is_partial"]
    assert m["changes"]["1y"] == pytest.approx((closes[-1] / closes[-253] - 1) * 100)


def test_compute_metrics_short_history_is_graceful():
    m = ind.compute_metrics(candles([100, 101, 102]))
    assert m["ma"]["200"] is None and m["rsi14"] is None and m["range_is_partial"]
    with pytest.raises(ValueError):
        ind.compute_metrics(candles([100]))


def test_find_similar_level():
    closes = [100] * 5 + [200] * 40 + [100.2]
    hit = ind.find_similar_level(candles(closes), tolerance_pct=0.5, min_gap_days=20)
    assert hit["close"] == 100  # the earlier visit, not the last few sessions
    assert ind.find_similar_level(candles([100, 101, 102]), 0.5, 20) is None
