import datetime as dt

from marketdaily import news

NOW = dt.datetime(2026, 11, 13, 12, 0, tzinfo=dt.timezone.utc)


def rss(*items):
    body = "".join(f"<item><title>{t}</title><link>{l}</link><pubDate>{p}</pubDate></item>" for t, l, p in items)
    return f"<rss><channel>{body}</channel></rss>".encode()


def test_parse_dedupe_and_24h_window():
    feed_a = rss(("Sensex jumps 500 points as banks rally", "https://a/1", "Fri, 13 Nov 2026 10:00:00 GMT"),
                 ("Old story from last week", "https://a/2", "Fri, 06 Nov 2026 10:00:00 GMT"),
                 ("Crude oil slips on demand worries", "https://a/3", "Fri, 13 Nov 2026 06:00:00 GMT"))
    feed_b = rss(("Sensex jumps 500 points as banks rally - Mint", "https://b/1", "Fri, 13 Nov 2026 09:00:00 GMT"))
    feeds = [("A", "u1"), ("B", "u2"), ("C", "u3")]

    def fetch(url):
        if url == "u3":
            raise OSError("down")  # a dead feed must not break the run
        return feed_a if url == "u1" else feed_b

    out = news.collect(NOW, fetch=fetch, feeds=feeds)
    titles = [i["title"] for i in out]
    assert len(out) == 2 and "Old story from last week" not in titles
    assert out[0]["url"] == "https://a/1"            # newest first, duplicate dropped
    assert all(i["source"] in ("A", "B") for i in out)


def test_bad_xml_is_ignored():
    assert news.parse_rss(b"<not xml", "X") == []
