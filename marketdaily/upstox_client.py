"""Upstox API client (stdlib only). The access token is read ONLY from env UPSTOX_ACCESS_TOKEN,
is sent only in the Authorization header, and is never logged.

Endpoints used (Upstox API v2; set UPSTOX_HIST_VERSION=v3 to use the v3 historical path):
  GET /v2/market-quote/quotes?instrument_key=A,B,...     (full market quote; up to 500 keys)
  GET /v2/historical-candle/{key}/day/{to}/{from}         (daily candles, newest first)
  GET /v3/historical-candle/{key}/days/1/{to}/{from}
Instrument keys for stocks come from Upstox's public NSE instruments file (symbol -> NSE_EQ|ISIN).
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from . import config

BASE = "https://api.upstox.com"
INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
HISTORY_DAYS = 420  # ~ 1 year + enough for a 200-day average


class UpstoxError(Exception):
    pass


class UpstoxAuthError(UpstoxError):
    """401: token missing, invalid or expired (Upstox tokens expire daily)."""


def _default_http_get(url: str, headers: dict, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise UpstoxAuthError("Upstox returned 401 (token missing/invalid/expired)") from None
        raise UpstoxError(f"Upstox HTTP {e.code} for {urllib.parse.urlsplit(url).path}") from None
    except urllib.error.URLError as e:
        raise UpstoxError(f"Upstox network error: {e.reason}") from None


class UpstoxClient:
    def __init__(self, token: str | None = None, http_get: Callable[..., bytes] | None = None):
        token = token if token is not None else os.environ.get("UPSTOX_ACCESS_TOKEN", "")
        if not token.strip():
            raise UpstoxAuthError("UPSTOX_ACCESS_TOKEN is not set")
        self._headers = {"Accept": "application/json", "Authorization": f"Bearer {token.strip()}"}
        self._get = http_get or _default_http_get

    def _json(self, path: str, params: dict | None = None) -> dict:
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params, safe="|,")
        body = json.loads(self._get(url, self._headers))
        if body.get("status") not in (None, "success"):
            raise UpstoxError(f"Upstox error response for {path}")
        return body.get("data", {})

    # ---- quotes ----
    def quotes(self, keys: list[str]) -> dict[str, dict]:
        """Returns {instrument_key: quote}. Handles batching."""
        out: dict[str, dict] = {}
        for i in range(0, len(keys), 100):
            data = self._json("/v2/market-quote/quotes", {"instrument_key": ",".join(keys[i:i + 100])})
            for resp_key, q in data.items():
                k = q.get("instrument_token") or resp_key.replace(":", "|", 1)
                out[k] = q
        return out

    # ---- history ----
    def daily_candles(self, key: str, days: int = HISTORY_DAYS, today: dt.date | None = None,
                      version: str | None = None) -> list[dict]:
        today = today or dt.date.today()
        frm = (today - dt.timedelta(days=days)).isoformat()
        to = today.isoformat()
        version = version or os.environ.get("UPSTOX_HIST_VERSION", "v2")
        k = urllib.parse.quote(key, safe="")
        path = (f"/v3/historical-candle/{k}/days/1/{to}/{frm}" if version == "v3"
                else f"/v2/historical-candle/{k}/day/{to}/{frm}")
        raw = self._json(path).get("candles", [])
        candles = [{"d": str(r[0])[:10], "o": float(r[1]), "h": float(r[2]), "l": float(r[3]),
                    "c": float(r[4]), "v": float(r[5] or 0)} for r in raw]
        candles.sort(key=lambda c: c["d"])
        return candles

    # ---- instruments ----
    def nse_equity_keys(self, symbols: list[str], cache_file=None) -> dict[str, str]:
        """symbol -> 'NSE_EQ|ISIN', via Upstox's public instruments file (cached for the day)."""
        today = dt.date.today().isoformat()
        if cache_file is not None:
            cached = config.read_json(cache_file)
            if cached and cached.get("date") == today:
                return {s: cached["map"][s] for s in symbols if s in cached["map"]}
        raw = self._get(INSTRUMENTS_URL, {"Accept": "application/gzip"}, 120)
        rows = json.load(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8"))
        full = {r["trading_symbol"]: r["instrument_key"] for r in rows
                if r.get("segment") == "NSE_EQ" and r.get("instrument_type") == "EQ"}
        if cache_file is not None:
            config.write_json(cache_file, {"date": today, "map": {s: full[s] for s in symbols if s in full}})
        return {s: full[s] for s in symbols if s in full}


def _today_candle_from_quote(q: dict, day: str) -> dict | None:
    ohlc = q.get("ohlc") or {}
    last = q.get("last_price")
    if not last or not ohlc.get("open"):
        return None
    return {"d": day, "o": float(ohlc["open"]), "h": float(max(ohlc.get("high", last), last)),
            "l": float(min(ohlc.get("low", last), last)), "c": float(last), "v": float(q.get("volume") or 0)}


def fetch_indices(client: UpstoxClient, today: dt.date) -> dict:
    quotes = client.quotes([k for _, _, k, _ in config.INDICES])
    out = {}
    for key, name, ikey, _ in config.INDICES:
        candles = client.daily_candles(ikey, today=today)
        q = quotes.get(ikey)
        # The historical endpoint may not yet include today's session: add it from the live quote.
        if q and (not candles or candles[-1]["d"] < today.isoformat()):
            tc = _today_candle_from_quote(q, today.isoformat())
            if tc:
                candles.append(tc)
        if candles:
            out[key] = {"name": name, "candles": candles}
    return out


def fetch_stocks(client: UpstoxClient, symbols: list[str], cache_file=None) -> list[dict]:
    keys = client.nse_equity_keys(symbols, cache_file)
    if not keys:
        return []
    inv = {v: k for k, v in keys.items()}
    stocks = []
    for ikey, q in client.quotes(list(keys.values())).items():
        sym = inv.get(ikey)
        last = q.get("last_price")
        if not sym or not last:
            continue
        net = q.get("net_change")
        prev = (last - net) if net is not None else (q.get("ohlc") or {}).get("close")
        if prev:
            stocks.append({"symbol": sym, "last": float(last), "prev_close": float(prev),
                           "change_pct": (last / prev - 1) * 100})
    return stocks


def fetch_all(token: str | None, settings: config.Settings, today: dt.date,
              http_get: Callable[..., bytes] | None = None) -> dict:
    """Indices + stocks from Upstox, commodities from yfinance. Raises UpstoxError on failure."""
    from . import fallback
    client = UpstoxClient(token, http_get)
    data = {
        "source": "upstox",
        "indices": fetch_indices(client, today),
        "stocks": fetch_stocks(client, settings.nifty50_symbols(), settings.cache_dir / "nse_instruments.json"),
        "commodities": {},
    }
    try:
        data["commodities"] = fallback.fetch_commodities()
    except Exception as e:  # commodities are optional
        print(f"WARN: commodities unavailable ({type(e).__name__})")
    return data
