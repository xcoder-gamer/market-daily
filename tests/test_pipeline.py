"""End-to-end tests with mocked data: no network, no API keys."""
import datetime as dt
import json

import pytest

from marketdaily import analysis, config, history, main, mock, nse_calendar, upstox_client
from marketdaily import compliance as comp

DAY = "2026-11-13"  # a Friday that is not an NSE holiday


def run(settings, *extra, **kw):
    return main.run(["--date", DAY, *extra], settings=settings, **kw)


def read(p):
    return p.read_text(encoding="utf-8")


def test_mock_run_builds_bilingual_site(settings):
    assert run(settings, "--mock") == main.OK
    pub = settings.public_dir
    for p in ("en/index.html", "hi/index.html", f"posts/{DAY}/en/index.html", f"posts/{DAY}/hi/index.html",
              "en/archive/index.html", "en/markets/index.html", "en/learn/index.html", "hi/learn/index.html",
              "en/about/index.html", "en/disclaimer/index.html", "en/privacy/index.html", "en/contact/index.html",
              "sitemap.xml", "robots.txt", "en/feed.xml", "hi/feed.xml", "data.json", "assets/style.css"):
        assert (pub / p).exists(), p
    for lang in ("en", "hi"):
        html = read(pub / f"posts/{DAY}/{lang}/index.html")
        assert comp.has_disclaimer(html, lang)                      # in the post (and footer)
        assert html.count(comp.DISCLAIMER[lang]) >= 2
        assert f'hreflang="{"hi" if lang == "en" else "en"}"' in html
        assert 'application/ld+json' in html and '"@type": "Article"' in html
        assert 'data-ad-slot' in html and '<svg' in html
        assert comp.POV_CLOSING[lang] in html
        assert f'lang="{lang}"' in html
    for page in pub.rglob("index.html"):
        if page.parent == pub:
            continue
        lang = page.relative_to(pub).parts[0]
        if lang in ("en", "hi"):
            assert comp.DISCLAIMER[lang] in read(page), page      # every page footer


def test_post_and_scripts_are_compliant(settings):
    run(settings, "--mock")
    post = json.loads(read(settings.posts_dir / DAY / "post.json"))
    for lang in ("en", "hi"):
        assert comp.validate_post_content(post[lang], lang) == []
        script = read(settings.posts_dir / DAY / "youtube" / f"script_{lang}.txt")
        assert script.rstrip().endswith(comp.DISCLAIMER[lang])
        assert "SHORT" in script and "LONG" in script
        meta = json.loads(read(settings.posts_dir / DAY / "youtube" / f"meta_{lang}.json"))
        assert meta["title"] and meta["tags"] and comp.DISCLAIMER[lang] in meta["description"]


def test_run_is_idempotent(settings):
    run(settings, "--mock")
    post_file = settings.posts_dir / DAY / "post.json"
    first = read(post_file)
    assert run(settings, "--mock") == main.OK
    assert read(post_file) == first
    assert len(list(settings.history_dir.glob("*.json"))) == 1


def test_skips_weekend_and_holiday(settings):
    for d in ("2026-11-14", "2026-11-24"):  # Saturday, Guru Nanak holiday
        assert main.run(["--date", d], settings=settings) == main.OK
    assert not settings.posts_dir.exists() or not list(settings.posts_dir.glob("*"))
    assert (settings.public_dir / "en" / "index.html").exists()   # site still rebuilt for deployment


def test_calendar():
    h = nse_calendar.load_holidays(config.ROOT / "data" / "holidays.json")
    assert not nse_calendar.is_trading_day(dt.date(2026, 11, 14), h)
    assert not nse_calendar.is_trading_day(dt.date(2026, 12, 25), h)
    assert nse_calendar.is_trading_day(dt.date(2026, 11, 13), h)
    assert "_note" not in h


def test_empty_data_never_overwrites(settings):
    run(settings, "--mock")
    before = read(settings.data_json)
    assert history.save_data_json(settings, {"indices": {}}) is False
    assert read(settings.data_json) == before
    with pytest.raises(history.EmptyDataError):
        history.save_snapshot(settings, DAY, {"indices": {}})
    with pytest.raises(history.EmptyDataError):
        history.merge_candles(settings, "nifty50", [])
    assert not history.is_valid_market_data({"indices": {}})
    assert not history.is_valid_market_data({"indices": {"nifty50": {"candles": []}}})


def test_upstox_401_falls_back_loudly(settings, monkeypatch):
    monkeypatch.setenv("UPSTOX_ACCESS_TOKEN", "expired-token-xyz")

    def http_401(url, headers, timeout=30):
        raise upstox_client.UpstoxAuthError("401")

    def fake_fallback(s):
        d = mock.market_data(dt.date.fromisoformat(DAY))
        d["source"] = "fallback"
        return d

    monkeypatch.setattr(main.fallback, "fetch_all", fake_fallback)
    code = run(settings, "--no-news", "--no-llm", http_get=http_401)
    assert code == main.DEGRADED
    html = read(settings.public_dir / "posts" / DAY / "en" / "index.html")
    assert "fallback" in html and "expired-token-xyz" not in html
    assert json.loads(read(settings.data_json))["source"] == "fallback"


def test_missing_token_falls_back(settings, monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(main.fallback, "fetch_all", lambda s: {**mock.market_data(dt.date.fromisoformat(DAY)), "source": "fallback"})
    assert run(settings, "--no-news", "--no-llm") == main.DEGRADED


def test_all_sources_down_fails_and_keeps_old_data(settings, monkeypatch):
    run(settings, "--mock")
    before = read(settings.data_json)
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(main.fallback, "fetch_all", lambda s: {"source": "fallback", "indices": {}, "stocks": [], "commodities": {}})
    assert run(settings, "--no-news", "--no-llm", "--force") == main.FAILED
    assert read(settings.data_json) == before


def test_upstox_parsing_with_fake_http(settings, monkeypatch):
    """Quotes + candles parsed from Upstox-shaped JSON; token only appears in the Authorization header."""
    seen = []
    candles = [[f"2026-{m:02d}-{d:02d}T00:00:00+05:30", 100 + i, 101 + i, 99 + i, 100.5 + i, 1000, 0]
               for i, (m, d) in enumerate((10 + (j // 28), 1 + j % 28) for j in range(60))][::-1]  # newest first

    def fake_get(url, headers, timeout=30):
        seen.append((url, headers))
        if "market-quote/quotes" in url:
            return json.dumps({"status": "success", "data": {"NSE_INDEX:Nifty 50": {
                "instrument_token": "NSE_INDEX|Nifty 50", "last_price": 175.0, "net_change": 2.0,
                "ohlc": {"open": 170, "high": 176, "low": 169, "close": 173}}}}).encode()
        return json.dumps({"status": "success", "data": {"candles": candles}}).encode()

    client = upstox_client.UpstoxClient("tok-123", http_get=fake_get)
    out = upstox_client.fetch_indices(client, dt.date(2026, 12, 31))
    cs = out["nifty50"]["candles"]
    assert cs == sorted(cs, key=lambda c: c["d"]) and cs[-1]["d"] == "2026-12-31" and cs[-1]["c"] == 175.0
    assert all(h["Authorization"] == "Bearer tok-123" for _, h in seen)
    assert all("tok-123" not in u for u, _ in seen)
    assert "%7C" in seen[-1][0] or "Nifty%2050" in seen[-1][0]   # instrument key is URL-encoded


def test_upstox_requires_token(monkeypatch):
    monkeypatch.delenv("UPSTOX_ACCESS_TOKEN", raising=False)
    with pytest.raises(upstox_client.UpstoxAuthError):
        upstox_client.UpstoxClient()


# ---- LLM loop: reject -> regenerate -> template ----
def _facts(settings):
    run(settings, "--mock")
    return json.loads(read(settings.posts_dir / DAY / "post.json"))["facts"]


def _good_json(lang, n_news):
    close = comp.POV_CLOSING[lang]
    return json.dumps({"title": "Market wrap", "summary": ["Line one.", "Line two."], "what_happened": ["Banks led."],
                       "history": ["Near the middle of its range."],
                       "news": [{"source_idx": 0, "title": "Rates steady", "impact": "neutral", "why": "Rates affect loan costs."}],
                       "pov": {"bull": ["Earnings are steady."], "bear": ["Valuations look stretched."], "closing": "ignored"},
                       "watch": ["Global cues."]})


def test_llm_violation_is_fed_back_and_regenerated(settings):
    facts = _facts(settings)
    items = mock.news(dt.datetime.now(dt.timezone.utc))
    calls = []

    def llm(system, user):
        calls.append(user)
        if len(calls) == 1:
            return _good_json("en", 1).replace("Banks led.", "You should buy banks now.")
        return _good_json("en", 1)

    content, meta = analysis.generate_content(facts, items, "en", llm)
    assert meta["method"] == "llm" and meta["attempts"] == 2
    assert "REJECTED" in calls[1] and "advice-verb" in calls[1]
    assert content["pov"]["closing"] == comp.POV_CLOSING["en"]        # set by code, not the model
    assert content["news"][0]["url"] == items[0]["url"]               # source link mapped from the index


def test_llm_always_violating_falls_back_to_template(settings):
    facts = _facts(settings)
    bad = _good_json("en", 1).replace("Banks led.", "Sure shot winner, buy now.")
    content, meta = analysis.generate_content(facts, mock.news(dt.datetime.now(dt.timezone.utc)), "en", lambda s, u: bad)
    assert meta["method"] == "template" and meta["attempts"] == analysis.MAX_TRIES
    assert comp.validate_post_content(content, "en") == []


def test_llm_outage_falls_back_without_retry_storm(settings):
    facts = _facts(settings)
    n = []

    def llm(s, u):
        n.append(1)
        raise analysis.LLMError("Anthropic HTTP 529")

    _, meta = analysis.generate_content(facts, [], "hi", llm)
    assert meta["method"] == "template" and len(n) == 1


def test_llm_garbage_output_is_retried_then_template(settings):
    facts = _facts(settings)
    _, meta = analysis.generate_content(facts, [], "en", lambda s, u: "not json at all")
    assert meta["method"] == "template" and meta["attempts"] == analysis.MAX_TRIES


def test_template_rejects_headlines_that_break_rules(settings):
    facts = _facts(settings)
    news = [{"title": "5 stocks to buy today", "source": "X", "url": "https://x/1"},
            {"title": "RBI keeps rates steady", "source": "Y", "url": "https://x/2"}]
    c = analysis.template_content(facts, news, "en")
    assert [i["url"] for i in c["news"]] == ["https://x/2"]
