"""yfinance data: the automatic fallback for indices/stocks, and the permanent source for commodities."""
from __future__ import annotations

from . import config


def _yf():
    import yfinance as yf  # imported lazily so tests and mock runs need no network libs
    return yf


def _candles_from_history(df) -> list[dict]:
    out = []
    for ts, row in df.iterrows():
        if row.get("Close") != row.get("Close"):  # NaN
            continue
        out.append({"d": ts.strftime("%Y-%m-%d"), "o": float(row["Open"]), "h": float(row["High"]),
                    "l": float(row["Low"]), "c": float(row["Close"]), "v": float(row.get("Volume", 0) or 0)})
    return out


def fetch_commodities() -> dict:
    yf = _yf()
    out = {}
    for key, name, ticker in config.COMMODITIES:
        try:
            hist = yf.Ticker(ticker).history(period="1mo", interval="1d")
            candles = _candles_from_history(hist)
            if len(candles) >= 2:
                last, prev = candles[-1]["c"], candles[-2]["c"]
                out[key] = {"name": name, "last": last, "prev_close": prev, "change_pct": (last / prev - 1) * 100}
        except Exception as e:
            print(f"WARN: {ticker} unavailable ({type(e).__name__})")
    return out


def fetch_all(settings: config.Settings) -> dict:
    yf = _yf()
    indices = {}
    for key, name, _, ticker in config.INDICES:
        try:
            candles = _candles_from_history(yf.Ticker(ticker).history(period="2y", interval="1d"))
            if candles:
                indices[key] = {"name": name, "candles": candles}
        except Exception as e:
            print(f"WARN: {ticker} unavailable ({type(e).__name__})")
    stocks = []
    for sym in settings.nifty50_symbols():
        try:
            c = _candles_from_history(yf.Ticker(sym + ".NS").history(period="5d", interval="1d"))
            if len(c) >= 2:
                stocks.append({"symbol": sym, "last": c[-1]["c"], "prev_close": c[-2]["c"],
                               "change_pct": (c[-1]["c"] / c[-2]["c"] - 1) * 100})
        except Exception:
            continue
    return {"source": "fallback", "indices": indices, "stocks": stocks, "commodities": fetch_commodities()}
