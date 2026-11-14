"""Static-site generator: builds public/ from data/ (posts, candles, data.json). Pure functions + one entry point."""
from __future__ import annotations

import datetime as dt
import shutil
from email.utils import format_datetime
from pathlib import Path

from . import compliance as comp
from . import config, history
from . import indicators as ind
from .strings import ARTICLES, PAGES, UI, all_glossary, esc, glossary_for, slug_date

LANGS = config.LANGS

CSS = """
:root{--bg:#fbfaf7;--fg:#1d2330;--muted:#5d6676;--card:#ffffff;--border:#e3e0d8;--accent:#1f5fbf;--accent-fg:#fff;
--up:#0a7a3d;--down:#c0262d;--warn:#b26a00;--soft:#f1efe9;--shadow:0 1px 2px rgba(20,25,40,.06)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12151c;--fg:#e8eaf0;--muted:#9aa3b5;--card:#1a1f2a;
--border:#2b3242;--accent:#6aa5ff;--accent-fg:#0b1220;--up:#3ddc84;--down:#ff7a7a;--warn:#ffb454;--soft:#202636;--shadow:none}}
:root[data-theme=dark]{--bg:#12151c;--fg:#e8eaf0;--muted:#9aa3b5;--card:#1a1f2a;--border:#2b3242;--accent:#6aa5ff;--accent-fg:#0b1220;
--up:#3ddc84;--down:#ff7a7a;--warn:#ffb454;--soft:#202636;--shadow:none}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 system-ui,-apple-system,"Segoe UI","Noto Sans Devanagari",Mangal,sans-serif}
a{color:var(--accent)}img,svg{max-width:100%}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:var(--card);padding:8px;z-index:9}
header.site{border-bottom:1px solid var(--border);background:var(--card)}
.bar{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;justify-content:space-between;padding:10px 0}
.brand{font-weight:700;font-size:1.15rem;color:var(--fg);text-decoration:none}
nav.main{display:flex;flex-wrap:wrap;gap:4px 14px}nav.main a{color:var(--fg);text-decoration:none;padding:4px 0;border-bottom:2px solid transparent}
nav.main a[aria-current=page]{border-color:var(--accent)}
.tools{display:flex;gap:8px}.btn{border:1px solid var(--border);background:var(--card);color:var(--fg);border-radius:8px;padding:5px 11px;
cursor:pointer;font:inherit;font-size:.9rem;text-decoration:none;min-height:34px}
.tag{color:var(--muted);font-size:.9rem;margin:0}
main{padding:20px 0 40px}h1{font-size:1.65rem;line-height:1.25;margin:.2em 0 .4em}h2{font-size:1.25rem;margin:1.6em 0 .5em}h3{font-size:1.05rem;margin:1em 0 .3em}
.meta{color:var(--muted);font-size:.9rem}.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow);margin:14px 0}
.minute{border-left:4px solid var(--accent)}.minute p{margin:.3em 0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.idx .name{font-size:.85rem;color:var(--muted)}.idx .val{font-size:1.3rem;font-weight:700}
.up{color:var(--up)}.down{color:var(--down)}.chg{font-weight:600;white-space:nowrap}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:6px 8px;border-bottom:1px solid var(--border);text-align:right}
th:first-child,td:first-child{text-align:left}.scroll{overflow-x:auto}
.cols{display:grid;gap:12px;grid-template-columns:1fr}@media(min-width:640px){.cols{grid-template-columns:1fr 1fr}}
.bull{border-top:3px solid var(--up)}.bear{border-top:3px solid var(--down)}
.pill{display:inline-block;border-radius:999px;padding:1px 10px;font-size:.78rem;border:1px solid var(--border);background:var(--soft)}
.pill.positive{color:var(--up);border-color:var(--up)}.pill.negative{color:var(--down);border-color:var(--down)}
.news li{margin:0 0 14px}ul.clean{list-style:none;padding:0;margin:0}
.chart{width:100%;height:auto}.c-grid{stroke:var(--border);stroke-width:1}.c-line{fill:none;stroke:var(--accent);stroke-width:2}
.c-ma50{fill:none;stroke:var(--warn);stroke-width:1.4;stroke-dasharray:6 4}.c-ma200{fill:none;stroke:var(--muted);stroke-width:1.4;stroke-dasharray:2 4}
.c-text{fill:var(--muted);font-size:11px}.spark{width:100%;height:36px}
.range{position:relative;height:8px;border-radius:4px;background:linear-gradient(90deg,var(--down),var(--soft),var(--up));margin:8px 0}
.range i{position:absolute;top:-4px;width:4px;height:16px;border-radius:2px;background:var(--fg)}
.gloss{background:var(--soft)}.gloss dt{font-weight:700;margin-top:.7em}.gloss dd{margin:0 0 0 0}
.disc{border:2px solid var(--warn);border-radius:12px;padding:12px 16px;margin:24px 0;background:var(--card);font-size:.95rem}
.ad{margin:22px 0;padding:18px;border:1px dashed var(--border);border-radius:10px;text-align:center;color:var(--muted);font-size:.8rem;min-height:90px}
.warn{border-left:4px solid var(--warn);background:var(--soft);padding:8px 12px;border-radius:6px;margin:10px 0;font-size:.95rem}
footer.site{border-top:1px solid var(--border);padding:20px 0 40px;font-size:.9rem;color:var(--muted)}footer.site nav{display:flex;gap:16px;flex-wrap:wrap}
.pn{display:flex;justify-content:space-between;gap:12px;margin-top:24px}
"""

JS = """(function(){
var d=document.documentElement;
document.addEventListener('click',function(e){
 var t=e.target.closest('[data-lang-toggle]');
 if(t){try{localStorage.setItem('md-lang',t.getAttribute('data-lang-toggle'))}catch(x){}}
 var b=e.target.closest('#theme-btn');
 if(b){var cur=d.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
  var nx=cur==='dark'?'light':'dark';d.setAttribute('data-theme',nx);try{localStorage.setItem('md-theme',nx)}catch(x){}}
});
})();"""

HEAD_JS = """(function(){var d=document.documentElement;try{var t=localStorage.getItem('md-theme');if(t)d.setAttribute('data-theme',t);
var l=localStorage.getItem('md-lang'),a=document.querySelector('meta[name=alt-url]');
if(l&&l!==d.lang&&a&&a.getAttribute('data-lang')===l){location.replace(a.content)}}catch(e){}})();"""


# ----------------------------------------------------------------------------- helpers
class Site:
    def __init__(self, settings: config.Settings):
        self.s = settings
        self.out = settings.public_dir

    def path(self, p: str) -> str:
        return self.s.base_path + p

    def abs(self, p: str) -> str:
        return (self.s.site_url or "https://example.com") + self.s.base_path + p

    def write(self, rel: str, content: str) -> None:
        f = self.out / rel.lstrip("/")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")


def fmt(x, d=2):
    return "–" if x is None else f"{x:,.{d}f}"


def chg_html(pct, with_arrow=True):
    if pct is None:
        return "–"
    cls = "up" if pct >= 0 else "down"
    arrow = ("▲ " if pct >= 0 else "▼ ") if with_arrow else ""
    return f'<span class="chg {cls}">{arrow}{pct:+.2f}%</span>'


def line_chart(candles: list[dict], title: str, w=640, h=230, days=252) -> str:
    """Inline SVG: 1y close + 50d and 200d averages (averages use the full history for correct values)."""
    closes = [c["c"] for c in candles]
    if len(closes) < 5:
        return ""
    ma50, ma200 = ind.sma_series(closes, 50), ind.sma_series(closes, 200)
    cut = max(0, len(closes) - days)
    xs = closes[cut:]
    dates = [c["d"] for c in candles][cut:]
    series = [("c-line", xs), ("c-ma50", ma50[cut:]), ("c-ma200", ma200[cut:])]
    vals = [v for _, s in series for v in s if v is not None]
    lo, hi = min(vals), max(vals)
    pad_l, pad_r, pad_t, pad_b = 52, 8, 8, 22
    iw, ih = w - pad_l - pad_r, h - pad_t - pad_b
    X = lambda i: pad_l + iw * (i / max(1, len(xs) - 1))
    Y = lambda v: pad_t + ih * (1 - (v - lo) / ((hi - lo) or 1))
    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>']
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        parts.append(f'<line class="c-grid" x1="{pad_l}" x2="{w - pad_r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                     f'<text class="c-text" x="{pad_l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v:,.0f}</text>')
    for cls, s in series:
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(s) if v is not None)
        if pts:
            parts.append(f'<polyline class="{cls}" points="{pts}"/>')
    parts.append(f'<text class="c-text" x="{pad_l}" y="{h - 5}">{esc(dates[0])}</text>'
                 f'<text class="c-text" x="{w - pad_r}" y="{h - 5}" text-anchor="end">{esc(dates[-1])}</text></svg>')
    return "".join(parts)


def sparkline(candles: list[dict], n=60) -> str:
    xs = [c["c"] for c in candles][-n:]
    if len(xs) < 3:
        return ""
    lo, hi = min(xs), max(xs)
    pts = " ".join(f"{100 * i / (len(xs) - 1):.1f},{34 - 32 * (v - lo) / ((hi - lo) or 1):.1f}" for i, v in enumerate(xs))
    return f'<svg class="spark" viewBox="0 0 100 36" preserveAspectRatio="none" aria-hidden="true"><polyline class="c-line" points="{pts}" vector-effect="non-scaling-stroke"/></svg>'


def range_bar(pos: float) -> str:
    return f'<div class="range" aria-hidden="true"><i style="left:calc({max(0, min(100, pos)):.0f}% - 2px)"></i></div>'


# ----------------------------------------------------------------------------- page shell
def shell(site: Site, lang: str, rel: str, alt_rel: str | None, title: str, desc: str, body: str, *,
          nav_key: str = "", og_type: str = "website", jsonld: str = "", alts: dict | None = None) -> str:
    ui = UI[lang]
    other = "hi" if lang == "en" else "en"
    name = site.s.site_name
    full_title = f"{title} | {name}" if title != name else name
    alts = alts or ({lang: rel, other: alt_rel} if alt_rel else {lang: rel})
    hreflang = "".join(f'<link rel="alternate" hreflang="{l}" href="{esc(site.abs(p))}">' for l, p in alts.items())
    if "en" in alts:
        hreflang += f'<link rel="alternate" hreflang="x-default" href="{esc(site.abs(alts["en"]))}">'
    alt_meta = f'<meta name="alt-url" data-lang="{other}" content="{esc(site.path(alt_rel))}">' if alt_rel else ""
    nav = "".join(f'<a href="{site.path(f"/{lang}/" + ("" if k == "home" else k + "/"))}"' +
                  (' aria-current="page"' if k == nav_key else "") + f">{esc(lbl)}</a>" for k, lbl in ui["nav"].items())
    toggle = (f'<a class="btn" lang="{other}" hreflang="{other}" data-lang-toggle="{other}" title="{esc(ui["toggle_title"])}" '
              f'href="{site.path(alt_rel)}">{esc(ui["toggle_label"])}</a>') if alt_rel else ""
    foot = "".join(f'<a href="{site.path(f"/{lang}/{k}/")}">{esc(lbl)}</a>' for k, lbl in ui["footer_links"].items())
    return f"""<!doctype html>
<html lang="{ui['html_lang']}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(full_title)}</title><meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(site.abs(rel))}">{hreflang}{alt_meta}
<meta property="og:title" content="{esc(full_title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="{og_type}"><meta property="og:url" content="{esc(site.abs(rel))}"><meta property="og:site_name" content="{esc(name)}">
<meta property="og:locale" content="{'hi_IN' if lang == 'hi' else 'en_IN'}"><meta name="twitter:card" content="summary">
<link rel="alternate" type="application/rss+xml" title="{esc(name)} ({lang})" href="{site.path(f'/{lang}/feed.xml')}">
<link rel="stylesheet" href="{site.path('/assets/style.css')}"><script>{HEAD_JS}</script>{jsonld}</head>
<body><a class="skip" href="#main">{esc(ui['skip'])}</a>
<header class="site"><div class="wrap"><div class="bar"><a class="brand" href="{site.path(f'/{lang}/')}">{esc(name)}</a>
<div class="tools">{toggle}<button class="btn" id="theme-btn" type="button" aria-label="{esc(ui['theme'])}">◐</button></div></div>
<nav class="main" aria-label="Main">{nav}</nav></div></header>
<main id="main"><div class="wrap">{body}</div></main>
<footer class="site"><div class="wrap"><div class="disc" role="note">{esc(comp.DISCLAIMER[lang])}</div>
<nav>{foot}<a href="{site.path(f'/{lang}/feed.xml')}">{esc(ui['subscribe'])}</a></nav>
<p>© {dt.date.today().year} {esc(name)}</p></div></footer><script src="{site.path('/assets/app.js')}" defer></script></body></html>"""


def ad_slot(lang: str) -> str:
    return f'<div class="ad" data-ad-slot="placeholder">{esc(UI[lang]["ad_slot"])}</div>'  # AdSense code goes here later


def source_note(lang: str, source: str) -> str:
    ui = UI[lang]
    if source == "upstox":
        return f'<p class="meta">{esc(ui["source_label"])}: {esc(ui["src_upstox"])}</p>'
    key = "src_mock" if source == "mock" else "src_fallback"
    return f'<p class="warn">{esc(ui["source_label"])}: {esc(ui[key])}</p>'


# ----------------------------------------------------------------------------- sections
def stats_table(lang: str, indices: dict) -> str:
    ui = UI[lang]
    head = "".join(f"<th>{esc(ui['periods'][k])}</th>" for k in ("1d", "1w", "1m", "6m", "1y"))
    rows = ""
    for v in indices.values():
        ch = v["changes"]
        rows += (f"<tr><td>{esc(v['name'])}</td><td>{fmt(v['last'])}</td>" +
                 "".join(f"<td>{chg_html(ch.get(k), False)}</td>" for k in ("1d", "1w", "1m", "6m", "1y")) +
                 f"<td>{fmt(v['rsi14'], 0)}</td><td>{fmt(v['from_high_pct'], 1)}%</td></tr>")
    return (f'<div class="scroll"><table><thead><tr><th></th><th>{esc(ui["close"])}</th>{head}<th>RSI</th>'
            f'<th>{esc(ui["from_high"])}</th></tr></thead><tbody>{rows}</tbody></table></div>')


def post_text(c: dict) -> str:
    """All prose of a post, for glossary detection."""
    return " ".join(s for _, s in comp.iter_strings({k: v for k, v in c.items() if k != "news"})) + " " + \
        " ".join(i["title"] + " " + i["why"] for i in c["news"])


def render_post(site: Site, post: dict, lang: str, prev_d: str | None, next_d: str | None) -> tuple[str, str]:
    ui, c, date = UI[lang], post[lang], post["date"]
    facts = post["facts"]
    rel = f"/posts/{date}/{lang}/"
    other = "hi" if lang == "en" else "en"
    alt_rel = f"/posts/{date}/{other}/"
    body = [f'<article><p class="meta">{esc(slug_date(date, lang))}</p><h1>{esc(c["title"])}</h1>',
            source_note(lang, post["source"]),
            f'<section class="card minute"><h2 style="margin-top:0">{esc(ui["today_minute"])}</h2>' +
            "".join(f"<p>{esc(s)}</p>" for s in c["summary"]) + "</section>"]

    # charts: main NIFTY chart + other indices
    charts = ""
    for key, v in facts["indices"].items():
        series = history.load_series(site.s, key, upto=date)
        svg = line_chart(series, f"{v['name']} {ui['markets_title']}", h=230 if key == "nifty50" else 200)
        if svg:
            charts += f'<figure class="card" style="margin:12px 0"><figcaption><b>{esc(v["name"])}</b> {chg_html(v["change_pct"])}</figcaption>{svg}</figure>'
    body.append(f'<h2>{esc(ui["what_happened"])}</h2>' + "".join(f"<p>{esc(p)}</p>" for p in c["what_happened"]) +
                stats_table(lang, facts["indices"]) + charts + f'<p class="meta">{esc(ui["chart_note"])}</p>')
    nf = facts["indices"].get("nifty50") or next(iter(facts["indices"].values()))
    body.append(f'<h2>{esc(ui["history"])}</h2>{range_bar(nf["range_pos"])}'
                f'<p class="meta">{esc(ui["range52"])}: {fmt(nf["low52"])} – {fmt(nf["high52"])}'
                f'{" " + esc(ui["partial"]) if nf["range_is_partial"] else ""}</p>' +
                "".join(f"<p>{esc(p)}</p>" for p in c["history"]))
    body.append(ad_slot(lang))

    news_html = ""
    for it in c["news"]:
        news_html += (f'<li class="card"><span class="pill {esc(it["impact"])}">{esc(ui["impact"][it["impact"]])}</span>'
                      f'<h3 style="margin-top:.4em">{esc(it["title"])}</h3><p><b>{esc(ui["why"])}:</b> {esc(it["why"])}</p>'
                      f'<p class="meta">{esc(ui["read_at"])}: <a href="{esc(it["url"])}" rel="noopener nofollow" target="_blank">{esc(it["source"])}</a></p></li>')
    body.append(f'<h2>{esc(ui["news"])}</h2><ul class="clean news">{news_html}</ul>')

    pov = c["pov"]
    li = lambda xs: "".join(f"<li>{esc(x)}</li>" for x in xs)
    body.append(f'<h2>{esc(ui["pov"])}</h2><div class="cols"><section class="card bull"><h3>{esc(ui["bull"])}</h3><ul>{li(pov["bull"])}</ul></section>'
                f'<section class="card bear"><h3>{esc(ui["bear"])}</h3><ul>{li(pov["bear"])}</ul></section></div>'
                f'<p><strong>{esc(pov["closing"])}</strong></p>')
    body.append(f'<h2>{esc(ui["watch"])}</h2><ul>{li(c["watch"])}</ul>')

    terms = glossary_for(post_text(c), lang)
    if terms:
        body.append(f'<aside class="card gloss"><h2 style="margin-top:0">{esc(ui["glossary_box"])}</h2><dl>' +
                    "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in terms) + "</dl></aside>")
    body.append(f'<div class="disc" role="note">{esc(comp.DISCLAIMER[lang])}</div></article>')
    pn = ""
    if prev_d:
        pn += f'<a href="{site.path(f"/posts/{prev_d}/{lang}/")}">← {esc(slug_date(prev_d, lang))}</a>'
    if next_d:
        pn += f'<a href="{site.path(f"/posts/{next_d}/{lang}/")}">{esc(slug_date(next_d, lang))} →</a>'
    body.append(f'<div class="pn">{pn}</div>')

    desc = " ".join(c["summary"])
    ld = ('<script type="application/ld+json">' + __import__("json").dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": c["title"][:110], "description": desc,
        "inLanguage": lang, "datePublished": date, "dateModified": date,
        "author": {"@type": "Person", "name": site.s.author},
        "publisher": {"@type": "Organization", "name": site.s.site_name},
        "mainEntityOfPage": site.abs(rel)}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    html = shell(site, lang, rel, alt_rel, c["title"], desc, "".join(body), nav_key="archive", og_type="article", jsonld=ld,
                 alts={"en": f"/posts/{date}/en/", "hi": f"/posts/{date}/hi/"})
    return rel, html


def dashboard(site: Site, lang: str, data: dict | None) -> str:
    if not data:
        return ""
    ui = UI[lang]
    cards = ""
    for key, v in data["indices"].items():
        series = history.load_series(site.s, key)
        cards += (f'<div class="card idx"><div class="name">{esc(v["name"])}</div><div class="val">{fmt(v["last"])}</div>'
                  f'{chg_html(v["change_pct"])}{sparkline(series)}</div>')
    gl = lambda xs: "".join(f"<tr><td>{esc(x['symbol'])}</td><td>{fmt(x['last'])}</td><td>{chg_html(x['change_pct'], False)}</td></tr>" for x in xs)
    tbl = lambda title, xs: (f'<div class="card"><h3 style="margin-top:0">{esc(title)}</h3><table><tbody>{gl(xs)}</tbody></table></div>') if xs else ""
    com = "".join(f"<tr><td>{esc(v['name'])}</td><td>{fmt(v['last'])}</td><td>{chg_html(v['change_pct'], False)}</td></tr>"
                  for v in data.get("commodities", {}).values())
    return (f'<section><h2>{esc(ui["dashboard"])}</h2><p class="meta">{esc(ui["updated"])}: {esc(slug_date(data["date"], lang))}</p>'
            f'{source_note(lang, data["source"])}<div class="grid">{cards}</div>'
            f'<div class="cols">{tbl(ui["gainers"], data.get("gainers", [])[:5])}{tbl(ui["losers"], data.get("losers", [])[:5])}</div>' +
            (f'<div class="card"><h3 style="margin-top:0">{esc(ui["commodities"])}</h3><table><tbody>{com}</tbody></table></div>' if com else "") +
            "</section>")


def post_list(site: Site, lang: str, posts: list[dict]) -> str:
    return '<ul class="clean">' + "".join(
        f'<li class="card"><span class="meta">{esc(slug_date(p["date"], lang))}</span><br>'
        f'<a href="{site.path(f"/posts/{p['date']}/{lang}/")}"><b>{esc(p[lang]["title"])}</b></a></li>' for p in posts) + "</ul>"


# ----------------------------------------------------------------------------- pages
def page_home(site, lang, posts, data):
    ui = UI[lang]
    if posts:
        p = posts[0]
        latest = (f'<section class="card minute"><p class="meta">{esc(ui["latest_post"])} · {esc(slug_date(p["date"], lang))}</p>'
                  f'<h1 style="font-size:1.4rem"><a href="{site.path(f"/posts/{p['date']}/{lang}/")}" style="color:inherit;text-decoration:none">{esc(p[lang]["title"])}</a></h1>' +
                  "".join(f"<p>{esc(s)}</p>" for s in p[lang]["summary"]) +
                  f'<p><a class="btn" href="{site.path(f"/posts/{p['date']}/{lang}/")}">{esc(ui["read_more"])} →</a></p></section>')
    else:
        latest = f'<p class="card">{esc(ui["no_posts"])}</p>'
    recent = f'<h2>{esc(ui["recent"])}</h2>{post_list(site, lang, posts[1:6])}' if len(posts) > 1 else ""
    body = f'<p class="tag">{esc(ui["tagline"])}</p>{latest}{dashboard(site, lang, data)}{ad_slot(lang)}{recent}'
    rel, alt = f"/{lang}/", f"/{'hi' if lang == 'en' else 'en'}/"
    return rel, shell(site, lang, rel, alt, site.s.site_name, ui["tagline"], body, nav_key="home")


def page_archive(site, lang, posts):
    ui = UI[lang]
    by_month: dict[str, list] = {}
    for p in posts:
        by_month.setdefault(p["date"][:7], []).append(p)
    body = f'<h1>{esc(ui["archive_title"])}</h1>' + ("".join(
        f'<h2>{esc(slug_date(m + "-01", lang).split(" ", 1)[1])}</h2>{post_list(site, lang, ps)}' for m, ps in by_month.items())
        or f'<p>{esc(ui["no_posts"])}</p>')
    rel, alt = f"/{lang}/archive/", f"/{'hi' if lang == 'en' else 'en'}/archive/"
    return rel, shell(site, lang, rel, alt, ui["archive_title"], ui["archive_title"], body, nav_key="archive")


def page_markets(site, lang):
    ui = UI[lang]
    body = f'<h1>{esc(ui["markets_title"])}</h1><p class="meta">{esc(ui["chart_note"])}</p>'
    for key, name, _, _ in config.INDICES:
        series = history.load_series(site.s, key)
        if len(series) < 2:
            continue
        m = ind.compute_metrics(series)
        rows = "".join(f"<tr><td>{esc(ui['periods'][k])}</td><td>{chg_html(m['changes'][k], False)}</td></tr>" for k in ("1d", "1w", "1m", "6m", "1y"))
        ma = "".join(f"<tr><td>{n}-day</td><td>{fmt(m['ma'][n])}</td></tr>" for n in ("20", "50", "200"))
        body += (f'<section class="card"><h2 style="margin-top:0">{esc(name)} · {fmt(m["last"])} {chg_html(m["change_pct"])}</h2>'
                 f'{line_chart(series, name + " " + ui["markets_title"])}{range_bar(m["range_pos"])}'
                 f'<p class="meta">{esc(ui["range52"])}: {fmt(m["low52"])} – {fmt(m["high52"])} · {esc(ui["from_high"])}: {fmt(m["from_high_pct"], 1)}% · RSI(14): {fmt(m["rsi14"], 0)}</p>'
                 f'<div class="cols"><table><tbody>{rows}</tbody></table><table><tbody><tr><th>{esc(ui["ma"])}</th><th></th></tr>{ma}'
                 f'<tr><td>{esc(ui["volatility"])}</td><td>{fmt(m["vol"]["daily_pct"]) + "%" if m["vol"] else "–"}</td></tr></tbody></table></div></section>')
    body += ad_slot(lang)
    rel, alt = f"/{lang}/markets/", f"/{'hi' if lang == 'en' else 'en'}/markets/"
    return rel, shell(site, lang, rel, alt, ui["markets_title"], ui["markets_title"], body, nav_key="markets")


def page_learn(site, lang):
    ui = UI[lang]
    arts = "".join(f'<section class="card"><h2 style="margin-top:0">{esc(t)}</h2>' + "".join(f"<p>{esc(p)}</p>" for p in ps) + "</section>"
                   for t, ps in ARTICLES[lang])
    gl = "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in all_glossary(lang))
    body = (f'<h1>{esc(ui["learn_title"])}</h1><p>{esc(PAGES[lang]["learn_intro"])}</p>{arts}'
            f'<aside class="card gloss"><h2 style="margin-top:0">{esc(ui["glossary"])}</h2><dl>{gl}</dl></aside>{ad_slot(lang)}')
    rel, alt = f"/{lang}/learn/", f"/{'hi' if lang == 'en' else 'en'}/learn/"
    return rel, shell(site, lang, rel, alt, ui["learn_title"], PAGES[lang]["learn_intro"], body, nav_key="learn")


def page_static(site, lang, key):
    title, paras = PAGES[lang][key]
    body = f"<h1>{esc(title)}</h1>" + "".join(f"<p>{esc(p)}</p>" for p in paras)
    if key == "contact":
        body += f'<p><a href="mailto:{esc(site.s.contact_email)}">{esc(site.s.contact_email)}</a></p>'
    if key == "disclaimer":
        body += f'<div class="disc">{esc(comp.DISCLAIMER[lang])}</div>'
    body += ad_slot(lang)
    rel, alt = f"/{lang}/{key}/", f"/{'hi' if lang == 'en' else 'en'}/{key}/"
    return rel, shell(site, lang, rel, alt, title, paras[0][:155], body, nav_key="about" if key == "about" else "")


def feed_xml(site: Site, lang: str, posts: list[dict]) -> str:
    items = ""
    for p in posts[:20]:
        c = p[lang]
        pub = format_datetime(dt.datetime.fromisoformat(p["date"] + "T16:30:00+05:30"))
        link = site.abs(f"/posts/{p['date']}/{lang}/")
        items += (f"<item><title>{esc(c['title'])}</title><link>{esc(link)}</link><guid>{esc(link)}</guid><pubDate>{pub}</pubDate>"
                  f"<description>{esc(' '.join(c['summary']) + ' ' + comp.DISCLAIMER[lang])}</description></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(site.s.site_name)}</title>'
            f'<link>{esc(site.abs(f"/{lang}/"))}</link><description>{esc(UI[lang]["tagline"])}</description><language>{lang}</language>{items}</channel></rss>')


def sitemap_xml(site: Site, rels: list[tuple[str, str | None]], lastmod: str) -> str:
    """rels: [(en_path, hi_path)] pairs."""
    out = ""
    for en, hi in rels:
        for path in (en, hi):
            alts = (f'<xhtml:link rel="alternate" hreflang="en" href="{esc(site.abs(en))}"/>'
                    f'<xhtml:link rel="alternate" hreflang="hi" href="{esc(site.abs(hi))}"/>')
            out += f"<url><loc>{esc(site.abs(path))}</loc><lastmod>{lastmod}</lastmod>{alts}</url>"
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            f'xmlns:xhtml="http://www.w3.org/1999/xhtml">{out}</urlset>')


def load_posts(settings: config.Settings) -> list[dict]:
    posts = []
    if settings.posts_dir.exists():
        for f in settings.posts_dir.glob("*/post.json"):
            p = config.read_json(f)
            if p and "en" in p and "hi" in p:
                posts.append(p)
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def build_site(settings: config.Settings) -> dict:
    """Rebuilds public/ completely. Returns {'pages': n, 'posts': n}."""
    site = Site(settings)
    if site.out.exists():
        shutil.rmtree(site.out)
    site.out.mkdir(parents=True)
    posts = load_posts(settings)
    data = config.read_json(settings.data_json)
    n = 0
    sitemap_pairs: list[tuple[str, str | None]] = []

    def emit(rel, html):
        nonlocal n
        site.write(rel + "index.html", html)
        n += 1

    site.write("assets/style.css", CSS)
    site.write("assets/app.js", JS)
    site.write("index.html", f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(settings.site_name)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="canonical" href="{esc(site.abs('/en/'))}">
<link rel="alternate" hreflang="en" href="{esc(site.abs('/en/'))}"><link rel="alternate" hreflang="hi" href="{esc(site.abs('/hi/'))}">
<link rel="alternate" hreflang="x-default" href="{esc(site.abs('/en/'))}">
<script>(function(){{var l='en';try{{l=localStorage.getItem('md-lang')||((navigator.language||'').slice(0,2)==='hi'?'hi':'en')}}catch(e){{}}
location.replace('{site.path('/')}'+(l==='hi'?'hi':'en')+'/')}})();</script>
<noscript><meta http-equiv="refresh" content="0;url={site.path('/en/')}"></noscript></head>
<body><p><a href="{site.path('/en/')}">English</a> · <a href="{site.path('/hi/')}">हिन्दी</a></p></body></html>""")
    site.write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {site.abs('/sitemap.xml')}\n")

    for lang in LANGS:
        emit(*page_home(site, lang, posts, data))
        emit(*page_archive(site, lang, posts))
        emit(*page_markets(site, lang))
        emit(*page_learn(site, lang))
        for key in ("about", "disclaimer", "privacy", "contact"):
            emit(*page_static(site, lang, key))
        site.write(f"{lang}/feed.xml", feed_xml(site, lang, posts))
    for path in ("", "archive/", "markets/", "learn/", "about/", "disclaimer/", "privacy/", "contact/"):
        sitemap_pairs.append((f"/en/{path}", f"/hi/{path}"))

    dates = [p["date"] for p in posts]
    for i, p in enumerate(posts):
        prev_d = dates[i + 1] if i + 1 < len(dates) else None
        next_d = dates[i - 1] if i > 0 else None
        for lang in LANGS:
            emit(*render_post(site, p, lang, prev_d, next_d))
        sitemap_pairs.append((f"/posts/{p['date']}/en/", f"/posts/{p['date']}/hi/"))

    site.write("sitemap.xml", sitemap_xml(site, sitemap_pairs, dates[0] if dates else dt.date.today().isoformat()))
    if data:
        site.write("data.json", __import__("json").dumps(data, ensure_ascii=False))
    return {"pages": n, "posts": len(posts)}
