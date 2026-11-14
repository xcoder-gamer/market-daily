"""Headline collection from free RSS feeds: dedupe, last 24 hours, newest first."""
from __future__ import annotations

import datetime as dt
import email.utils
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Callable

FEEDS = [
    ("Google News", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en"),
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("LiveMint", "https://www.livemint.com/rss/markets"),
]
UA = "Mozilla/5.0 (compatible; MarketDailyBot/1.0)"


def _fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _parse_date(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s.strip())
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def parse_rss(xml_bytes: bytes, source: str) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = _parse_date(it.findtext("pubDate"))
        if title and link and pub:
            src = it.findtext("source") or source  # Google News names the real publisher here
            items.append({"title": title, "url": link, "source": src.strip(), "published": pub.isoformat()})
    return items


_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "as", "at", "by", "is", "are", "with", "after"}


def _tokens(title: str) -> frozenset:
    t = re.sub(r"\s+[-|–—]\s+[^-|–—]{2,40}$", "", title)  # drop trailing " - Publisher"
    return frozenset(w for w in re.findall(r"[a-z0-9]+", t.lower()) if w not in _STOP)


def dedupe(items: list[dict], threshold: float = 0.7) -> list[dict]:
    kept, seen = [], []
    for it in items:
        tk = _tokens(it["title"])
        if not tk:
            continue
        if any(len(tk & s) / len(tk | s) >= threshold for s in seen):
            continue
        seen.append(tk)
        kept.append(it)
    return kept


def collect(now: dt.datetime | None = None, fetch: Callable[[str], bytes] = _fetch,
            feeds=FEEDS, hours: int = 24, limit: int = 40) -> list[dict]:
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=hours)
    items: list[dict] = []
    for source, url in feeds:
        try:
            items += parse_rss(fetch(url), source)
        except Exception as e:  # one dead feed must not stop the run
            print(f"WARN: feed {source} failed ({type(e).__name__})")
    recent = [i for i in items if cutoff <= dt.datetime.fromisoformat(i["published"]) <= now + dt.timedelta(hours=1)]
    recent.sort(key=lambda i: i["published"], reverse=True)
    return dedupe(recent)[:limit]
