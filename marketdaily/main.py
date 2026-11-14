"""Daily orchestrator.

Exit codes: 0 ok | 3 completed but DEGRADED (fallback data source) | 1 failed.
The GitHub workflow publishes the site in every case, then fails the job on 1 or 3 so you get an email."""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

from . import analysis, config, fallback, history, mock, news, nse_calendar, render, upstox_client, youtube
from . import indicators as ind

OK, DEGRADED, FAILED = 0, 3, 1

for _s in (sys.stdout, sys.stderr):  # Hindi in log lines must not crash a cp1252 Windows console
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def _gh(level: str, msg: str) -> None:
    print(f"::{level}::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"{level.upper()}: {msg}")


def acquire(s: config.Settings, today: dt.date, use_mock: bool, http_get=None) -> tuple[dict | None, bool]:
    """Returns (data, degraded). Upstox first; any Upstox failure falls back to yfinance and marks degraded."""
    if use_mock:
        return mock.market_data(today), False
    try:
        data = upstox_client.fetch_all(os.environ.get("UPSTOX_ACCESS_TOKEN"), s, today, http_get)
        if history.is_valid_market_data(data):
            return data, False
        _gh("error", "Upstox returned incomplete data (NIFTY 50 history missing); using fallback")
    except upstox_client.UpstoxAuthError as e:
        _gh("error", f"Upstox token problem: {e}. Refresh the UPSTOX_ACCESS_TOKEN secret. Using fallback data.")
    except upstox_client.UpstoxError as e:
        _gh("error", f"Upstox failed: {e}. Using fallback data.")
    try:
        data = fallback.fetch_all(s)
    except Exception as e:  # yfinance missing / offline
        _gh("error", f"Fallback data source failed too: {type(e).__name__}")
        return None, True
    return (data if history.is_valid_market_data(data) else None), True


def run(argv: list[str] | None = None, settings: config.Settings | None = None, http_get=None, llm=None) -> int:
    ap = argparse.ArgumentParser(prog="marketdaily")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--mock", action="store_true", help="offline synthetic data (no network, no LLM)")
    ap.add_argument("--force", action="store_true", help="run on non-trading days / regenerate an existing post")
    ap.add_argument("--no-llm", action="store_true", help="use the deterministic template text")
    ap.add_argument("--no-news", action="store_true")
    ap.add_argument("--render-only", action="store_true", help="only rebuild the static site from stored data")
    ap.add_argument("--root", help="project root (default: this repo)")
    args = ap.parse_args(argv)

    s = settings or config.Settings.from_env(args.root)
    today = dt.date.fromisoformat(args.date) if args.date else nse_calendar.today_ist()

    if args.render_only:
        print("rendered", render.build_site(s))
        return OK

    holidays = nse_calendar.load_holidays(s.holidays_file)
    if not args.mock and not args.force and not nse_calendar.is_trading_day(today, holidays):
        print(f"{today}: not a trading day ({nse_calendar.skip_reason(today, holidays)}); only rebuilding the site")
        render.build_site(s)
        return OK

    data, degraded = acquire(s, today, args.mock, http_get)
    if data is None:
        _gh("error", "No valid market data from any source. Nothing was overwritten.")
        render.build_site(s)
        return FAILED
    source = data["source"]

    # ---- persist candles (merged series), compute metrics on the full stored history
    indices = {}
    for key, v in data["indices"].items():
        series = history.merge_candles(s, key, v["candles"])
        if len(series) < 2:
            continue
        indices[key] = {"name": v["name"], "metrics": ind.compute_metrics(series), "similar": ind.find_similar_level(series)}
    if "nifty50" not in indices:
        _gh("error", "NIFTY 50 metrics unavailable")
        return FAILED
    date = indices["nifty50"]["metrics"]["date"]  # the actual trading date of the data
    facts = analysis.build_facts(date, source, indices, data.get("stocks", []), data.get("commodities", {}))

    # ---- public data.json + dated snapshot (never empty)
    payload = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "date": date, "source": source,
        "indices": {k: {kk: v[kk] for kk in ("name", "last", "change", "change_pct", "changes", "rsi14", "ma", "high52",
                                              "low52", "from_high_pct", "range_pos")} for k, v in facts["indices"].items()},
        "commodities": facts["commodities"], "gainers": facts["gainers"], "losers": facts["losers"], "latest_post": date,
    }
    history.save_snapshot(s, date, facts)
    history.save_data_json(s, payload)

    post_file = s.posts_dir / date / "post.json"
    if post_file.exists() and not args.force:
        print(f"{date}: post already exists; skipping generation (idempotent). Use --force to regenerate.")
    else:
        if args.mock:
            items = mock.news(dt.datetime.now(dt.timezone.utc))
        else:
            items = [] if args.no_news else news.collect()
        if items:
            config.write_json(s.news_dir / f"{date}.json", items)
        elif not args.mock and not args.no_news:
            _gh("warning", "No news headlines were fetched; the post will have a short news section")
        model_llm = None if (args.mock or args.no_llm) else (llm or analysis.llm_from_env(s.anthropic_model))
        post = analysis.build_post(facts, items, model_llm)
        for lang in config.LANGS:
            m = post["meta"][lang]
            print(f"{lang}: text by {m['method']} (attempts {m['attempts']}){' - ' + m['note'] if m['note'] else ''}")
            if model_llm is None and not (args.mock or args.no_llm):
                _gh("warning", "ANTHROPIC_API_KEY not set: posts use template text instead of AI analysis")
        config.write_json(post_file, post)
        yt = youtube.write_all(s, post, s.site_url)
        if s.enable_video:
            from . import video
            for lang in config.LANGS:
                try:
                    video.render(s, post, lang, yt[lang]["short"])
                except Exception as e:
                    _gh("warning", f"video render failed for {lang}: {type(e).__name__}")

    print("site:", render.build_site(s))
    if degraded:
        _gh("error", "Published with FALLBACK data (Upstox unavailable). Failing this run so you are notified.")
        return DEGRADED
    return OK


if __name__ == "__main__":
    sys.exit(run())
