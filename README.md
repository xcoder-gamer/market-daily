# Market Daily: bilingual (English + हिन्दी) daily market blog

Every trading day at 4:30 PM IST a GitHub Action pulls Indian market data, adds historical context and news, writes a
blog post in **English and Hindi**, builds a static site, publishes it to GitHub Pages, and drafts YouTube scripts.
No manual steps once configured.

> **Compliance first.** The author is not a SEBI-registered investment advisor. Generated text may describe and explain,
> never recommend. This is enforced three times: in the LLM prompt, by a post-generation filter that rejects and
> regenerates violating text (falls back to a safe template after 3 tries), and by tests. See "Compliance" below.

## What's here

```
marketdaily/
  upstox_client.py  Upstox API (quotes, daily candles, NSE instrument keys). Token only from env.
  fallback.py       yfinance: automatic fallback for indices/stocks; permanent source for gold/silver/crude/USDINR
  history.py        merged candle series + data/history/YYYY-MM-DD.json snapshots; never writes empty data
  indicators.py     SMA 20/50/200, RSI(14, Wilder), 1d/1w/1m/6m/1y change, 52w high/low distance, volatility
  news.py           RSS (Google News, Economic Times, Moneycontrol, LiveMint): dedupe, last 24h
  analysis.py       LLM prompts (Anthropic), compliance loop, deterministic template fallback
  compliance.py     banned-pattern filter (EN + HI), disclaimer text, POV rules
  render.py         static site: pages, inline-SVG charts, sitemap, robots, RSS, JSON-LD, hreflang
  youtube.py        script_en/hi.txt (Short + Long), title, description, tags
  video.py          OPTIONAL ElevenLabs voiceover + ffmpeg slideshow (ENABLE_VIDEO=1)
  mock.py           deterministic offline data for local testing
  main.py           orchestrator (exit 0 ok, 3 = used fallback data, 1 = failed)
data/holidays.json  NSE holidays (skip list)        data/nifty50.json  optional constituent override
tests/              indicators, compliance filter, pipeline with mocked data, news, Upstox parsing
.github/workflows/daily.yml
```

Generated and committed by the workflow: `data/candles/`, `data/history/`, `data/posts/YYYY-MM-DD/` (post.json +
`youtube/`), `data/news/`, `data.json`. The site itself (`public/`) is rebuilt from those each run and deployed, not committed.

Site layout: `/en/` and `/hi/` (Home, Archive, Markets, Learn, About, Disclaimer, Privacy, Contact),
posts at `/posts/YYYY-MM-DD/en/` and `/posts/YYYY-MM-DD/hi/`, `/sitemap.xml`, `/robots.txt`, `/en/feed.xml`, `/hi/feed.xml`.

## Setup

1. **Put this folder in its own GitHub repo** (the workflow must be at the repo root: `.github/workflows/daily.yml`).
2. **Secrets** (Settings → Secrets and variables → Actions → *Secrets*):
   | Name | Needed | Notes |
   |---|---|---|
   | `UPSTOX_ACCESS_TOKEN` | recommended | without it the run uses yfinance and **fails loudly** (by design) |
   | `ANTHROPIC_API_KEY` | recommended | without it posts use template text, no AI analysis |
   | `ELEVENLABS_API_KEY` | only if video on | |
3. **Variables** (same page → *Variables*): `SITE_URL` (e.g. `https://yourdomain.com`), `SITE_BASE_PATH` (empty for a
   custom domain; `/repo-name` for `user.github.io/repo-name`), `SITE_NAME`, `SITE_AUTHOR`, `CONTACT_EMAIL`,
   optional `ANTHROPIC_MODEL` (default `claude-sonnet-5-5`), `ENABLE_VIDEO` (`1` to turn on), `ELEVENLABS_VOICE_ID_EN/HI`.
4. **Enable Pages**: Settings → Pages → Source: **GitHub Actions**.
5. **Custom domain**: Settings → Pages → Custom domain, then add the DNS records GitHub shows; tick *Enforce HTTPS*;
   set `SITE_URL` to it and leave `SITE_BASE_PATH` empty.
6. **Failure emails**: GitHub emails the person who last edited the workflow's cron on failed scheduled runs
   (Settings → Notifications → Actions). Confirm it's switched on for your account.
7. Run it once: Actions → *Daily market post* → *Run workflow* (tick *force* if it's a weekend/holiday).

### Upstox token: read this
Standard Upstox access tokens **expire every day**, so a fixed secret will return 401 the next morning. Check Upstox's
current docs for a long-lived *read-only/extended* token suited to market-data-only use, or refresh the secret daily.
When the token is dead the run still publishes (data marked "fallback" on the page) and then **fails on purpose** so you
get the email. I could not call the live Upstox API from here, so the endpoint paths (`/v2/market-quote/quotes`,
`/v2/historical-candle/...`, optional `UPSTOX_HIST_VERSION=v3`) follow their documentation from memory: **verify them
with one real run** and adjust `upstox_client.py` if a field name differs.

## Run locally

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q                       # tests
python -m marketdaily --mock              # full offline run with synthetic data -> public/
python -m http.server 8000 -d public      # then open http://localhost:8000/
# live (needs env vars from .env.example exported):
python -m marketdaily --force --date 2026-11-13
```
Flags: `--mock`, `--no-llm`, `--no-news`, `--force`, `--render-only`, `--date YYYY-MM-DD`, `--root PATH`.
The run is idempotent: an existing post for that trading date is kept unless `--force`.

## Compliance (hard requirements)
- Banned (EN and HI): buy/sell/hold/accumulate calls and advice phrasing, price targets, stop-losses, entry/exit levels,
  "will go up/down" certainty, tips, guarantees, hype words ("sure shot", "jackpot", "multibagger"...), "stocks to buy".
- Each rejection is fed back to the model as a list of the exact problems; 3 failures → deterministic template.
- The "My point of view" closing line telling the reader to do their own analysis is **added by code**, not the model,
  and the filter fails any post where it is missing or either the bull or bear side is empty.
- The full disclaimer sits in every page footer and in every post, in the page's language. YouTube scripts end with it.
- News is summarised in the model's own words; each item links to the source, headline text is not republished
  (only the no-AI template shows headlines, and only ones that pass the filter).
- The filter is regex-based, so it is strict but not perfect. **Read the first posts before trusting it**, and extend the
  pattern lists in `compliance.py` (each addition should get a test). Not legal advice; consider asking a professional
  whether your content needs SEBI registration (research analyst / investment adviser rules).

## Known limitations
- **Moneycontrol's RSS returns 403 to automated clients** (tested). The run tolerates dead feeds, so you simply get
  three sources; replace or drop it in `news.py` `FEEDS`.
- Holidays: `data/holidays.json` is the 2026 NSE list; add 2027 when NSE publishes it. An unlisted holiday is harmless:
  the data's last date doesn't change, so the existing post is kept.
- NIFTY 50 constituents change; edit `data/nifty50.json` (list of NSE symbols) to override the built-in list. Symbols
  Upstox can't resolve are skipped.
- "Live dashboard" is the latest daily close, rebuilt each run (not intraday).
- Video (`ENABLE_VIDEO=1`) is untested here; run it manually once (needs ffmpeg, matplotlib, ElevenLabs voices).
- The Hindi text is written natively by the model; have a Hindi reader skim the first few posts.
- AdSense: each page has a placeholder `<div data-ad-slot="placeholder">`; no ad code is included.
