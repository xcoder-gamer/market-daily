"""YouTube package per language, built from the SAME analysis as the blog post: a 60-90s Short script,
a ~5 minute long script, title, description and tags. Always ends with the disclaimer; compliance-checked."""
from __future__ import annotations

from . import compliance as comp
from . import config
from .strings import slug_date

TAGS = {
    "en": ["Nifty 50", "Sensex", "Bank Nifty", "Indian stock market", "share market today", "market analysis",
           "stock market for beginners", "market wrap", "Nifty IT", "financial education"],
    "hi": ["निफ्टी 50", "सेंसेक्स", "बैंक निफ्टी", "शेयर बाज़ार", "आज का बाज़ार", "बाज़ार का विश्लेषण",
           "शेयर बाज़ार हिंदी में", "शुरुआती निवेशकों के लिए", "वित्तीय शिक्षा"],
}
FRAME = {
    "en": {"hi": "Hello, and welcome to {name}. Here is what happened in the Indian market on {date}.",
           "hist": "Now, some context from history.", "news": "Next, the news that mattered.",
           "pov": "Here is my point of view. This is a balanced look at both sides.", "bull": "On the optimistic side:",
           "bear": "On the cautious side:", "watch": "And here is what to watch tomorrow.",
           "out": "If this was useful, subscribe for tomorrow's market note. Thanks for watching.",
           "why": "Why it may matter:", "disc": "Disclaimer:", "head": "Today's wrap", "what": "What happened today."},
    "hi": {"hi": "नमस्कार, {name} में आपका स्वागत है। {date} को भारतीय बाज़ार में क्या हुआ, आइए देखते हैं।",
           "hist": "अब थोड़ा पुराने आँकड़ों का संदर्भ।", "news": "अब वे ख़बरें जो आज मायने रखती थीं।",
           "pov": "अब मेरा नज़रिया। यह दोनों पक्षों पर संतुलित नज़र है।", "bull": "उम्मीद वाले पक्ष में:",
           "bear": "सावधानी वाले पक्ष में:", "watch": "और कल इन बातों पर नज़र रखिए।",
           "out": "अगर यह काम का लगा हो तो कल के बाज़ार नोट के लिए सब्सक्राइब करें। देखने के लिए धन्यवाद।",
           "why": "यह क्यों मायने रख सकता है:", "disc": "अस्वीकरण:", "head": "आज का सार", "what": "आज क्या हुआ।"},
}


def build(post: dict, lang: str, site_name: str, page_url: str) -> dict:
    c, f, date = post[lang], FRAME[lang], post["date"]
    ds = slug_date(date, lang)
    intro = f["hi"].format(name=site_name, date=ds)
    disc = comp.DISCLAIMER[lang]

    short = [intro, *c["summary"], c["history"][1] if len(c["history"]) > 1 else c["history"][0]]
    if c["news"]:
        short += [c["news"][0]["title"] + ".", f["why"] + " " + c["news"][0]["why"]]
    short += [f["bull"] + " " + c["pov"]["bull"][0], f["bear"] + " " + c["pov"]["bear"][0], c["pov"]["closing"], f["out"], disc]

    long_ = [intro, *c["summary"], f["what"], *c["what_happened"], f["hist"], *c["history"], f["news"]]
    for it in c["news"]:
        long_ += [it["title"] + ".", f["why"] + " " + it["why"]]
    long_ += [f["pov"], f["bull"], *c["pov"]["bull"], f["bear"], *c["pov"]["bear"], c["pov"]["closing"], f["watch"],
              *c["watch"], f["out"], disc]

    meta = {
        "title": c["title"][:100],
        "description": "\n\n".join([" ".join(c["summary"]), page_url, disc]),
        "tags": TAGS[lang],
    }
    bad = [str(v) for s in short + long_ + [meta["title"], meta["description"]] for v in comp.check_text(s, lang)
           if s != disc]
    if bad:
        raise ValueError("YouTube script failed compliance: " + "; ".join(bad))
    words = lambda xs: sum(len(x.split()) for x in xs)
    return {"short": "\n\n".join(short), "long": "\n\n".join(long_), "meta": meta,
            "words": {"short": words(short), "long": words(long_)}}


def write_all(settings: config.Settings, post: dict, site_base_url: str) -> dict:
    out = settings.posts_dir / post["date"] / "youtube"
    out.mkdir(parents=True, exist_ok=True)
    result = {}
    for lang in config.LANGS:
        url = f"{site_base_url}{settings.base_path}/posts/{post['date']}/{lang}/"
        b = build(post, lang, settings.site_name, url)
        text = (f"TITLE: {b['meta']['title']}\n\nTAGS: {', '.join(b['meta']['tags'])}\n\n"
                f"DESCRIPTION:\n{b['meta']['description']}\n\n"
                f"===== SHORT (60-90 seconds, about {b['words']['short']} words) =====\n\n{b['short']}\n\n"
                f"===== LONG (about 5 minutes, about {b['words']['long']} words) =====\n\n{b['long']}\n")
        (out / f"script_{lang}.txt").write_text(text, encoding="utf-8")
        config.write_json(out / f"meta_{lang}.json", b["meta"])
        result[lang] = b
    return result
