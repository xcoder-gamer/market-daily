"""Turns computed facts + headlines into a bilingual post.

Flow per language: LLM draft -> compliance check -> (violations fed back, regenerate, up to MAX_TRIES)
-> if still non-compliant or no API key/outage: deterministic template text (always compliant, tested).
The POV closing line is always set by code, never by the model."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Callable

from . import compliance as comp
from .strings import slug_date

MAX_TRIES = 3
LLM = Callable[[str, str], str]  # (system, user) -> text


class LLMError(Exception):
    pass


# ----------------------------------------------------------------------------- facts
def _idx_facts(m: dict, similar: dict | None) -> dict:
    keep = ("date", "last", "change", "change_pct", "changes", "ma", "rsi14", "high52", "low52",
            "from_high_pct", "from_low_pct", "range_pos", "range_is_partial", "vol")
    d = {k: m[k] for k in keep}
    d["similar"] = similar
    return d


def build_facts(date: str, source: str, indices: dict, stocks: list[dict], commodities: dict) -> dict:
    """indices: {key: {'name', 'metrics', 'similar'}}"""
    ranked = sorted((s for s in stocks if s.get("change_pct") is not None), key=lambda s: s["change_pct"], reverse=True)
    pick = lambda xs: [{"symbol": s["symbol"], "change_pct": round(s["change_pct"], 2), "last": round(s["last"], 2)} for s in xs]
    return {
        "date": date, "source": source,
        "indices": {k: {"name": v["name"], **_idx_facts(v["metrics"], v.get("similar"))} for k, v in indices.items()},
        "gainers": pick(ranked[:5]),
        "losers": pick([s for s in ranked[-5:][::-1] if s["change_pct"] < 0] or ranked[-5:][::-1]),
        "commodities": {k: {"name": v["name"], "last": round(v["last"], 2), "change_pct": round(v["change_pct"], 2)}
                        for k, v in commodities.items()},
    }


# ----------------------------------------------------------------------------- formatting
def _n(x, d=2): return f"{x:,.{d}f}"
def _signed(x): return f"{x:+.2f}%"


def _zone(rsi, lang):
    if rsi is None: return {"en": "not available yet", "hi": "अभी उपलब्ध नहीं"}[lang]
    if rsi >= 70: return {"en": "in the 'stretched upward' zone", "hi": "'ज़्यादा खिंचे हुए' क्षेत्र में"}[lang]
    if rsi <= 30: return {"en": "in the 'stretched downward' zone", "hi": "'ज़्यादा गिरे हुए' क्षेत्र में"}[lang]
    return {"en": "in the middle zone", "hi": "बीच के क्षेत्र में"}[lang]


# ----------------------------------------------------------------------------- template (always compliant)
def template_content(facts: dict, news: list[dict], lang: str) -> dict:
    en = lang == "en"
    ix = facts["indices"]
    n = ix.get("nifty50") or next(iter(ix.values()))
    nm = n["name"]
    up = n["change"] >= 0
    date_s = slug_date(facts["date"], lang)
    rsi = n["rsi14"]

    if en:
        title = f"{nm} {'closes higher' if up else 'closes lower'} at {_n(n['last'])} ({_signed(n['change_pct'])}): market wrap for {date_s}"
    else:
        title = f"{nm} {_n(n['last'])} पर बंद, {'बढ़त' if up else 'गिरावट'} {_signed(n['change_pct'])}: {date_s} का बाज़ार सार"

    others = [v for k, v in ix.items() if v is not n]
    if en:
        s1 = f"{nm} ended {'up' if up else 'down'} {abs(n['change_pct']):.2f}% at {_n(n['last'])}" + \
             ("; " + ", ".join(f"{o['name']} {_signed(o['change_pct'])}" for o in others) if others else "") + "."
        s2 = f"It sits {abs(n['from_high_pct']):.1f}% below its 52-week high" + (f", and RSI is {rsi:.0f} ({_zone(rsi, 'en')})." if rsi else ".")
    else:
        s1 = f"{nm} {_n(n['last'])} पर बंद हुआ, {abs(n['change_pct']):.2f}% की {'बढ़त' if up else 'गिरावट'}" + \
             ("; " + ", ".join(f"{o['name']} {_signed(o['change_pct'])}" for o in others) if others else "") + "।"
        s2 = f"यह अपने 52 हफ़्ते के उच्च स्तर से {abs(n['from_high_pct']):.1f}% नीचे है" + (f", और RSI {rsi:.0f} है ({_zone(rsi, 'hi')})।" if rsi else "।")

    # what happened
    what = []
    if en:
        what.append(" ".join(f"{v['name']} closed at {_n(v['last'])} ({_signed(v['change_pct'])})." for v in ix.values()))
        if facts["gainers"]:
            what.append("Top NIFTY 50 gainers: " + ", ".join(f"{g['symbol']} ({_signed(g['change_pct'])})" for g in facts["gainers"][:3]) +
                        ". Top losers: " + ", ".join(f"{g['symbol']} ({_signed(g['change_pct'])})" for g in facts["losers"][:3]) + ".")
        if facts["commodities"]:
            what.append("Elsewhere: " + "; ".join(f"{c['name']} {_n(c['last'])} ({_signed(c['change_pct'])})" for c in facts["commodities"].values()) + ".")
    else:
        what.append(" ".join(f"{v['name']} {_n(v['last'])} पर बंद ({_signed(v['change_pct'])})।" for v in ix.values()))
        if facts["gainers"]:
            what.append("NIFTY 50 के टॉप गेनर: " + ", ".join(f"{g['symbol']} ({_signed(g['change_pct'])})" for g in facts["gainers"][:3]) +
                        "। टॉप लूज़र: " + ", ".join(f"{g['symbol']} ({_signed(g['change_pct'])})" for g in facts["losers"][:3]) + "।")
        if facts["commodities"]:
            what.append("बाकी बाज़ार: " + "; ".join(f"{c['name']} {_n(c['last'])} ({_signed(c['change_pct'])})" for c in facts["commodities"].values()) + "।")

    # history
    hist = []
    ch = n["changes"]
    fmt = lambda k: (_signed(ch[k]) if ch.get(k) is not None else "n/a")
    ma = n["ma"]
    rel = lambda v: ((("above" if n["last"] >= v else "below") if en else ("ऊपर" if n["last"] >= v else "नीचे")) if v else None)
    if en:
        hist.append(f"Over the past week, month, six months and year, {nm} has moved {fmt('1w')}, {fmt('1m')}, {fmt('6m')} and {fmt('1y')}.")
        hist.append(f"Its 52-week range is {_n(n['low52'])} to {_n(n['high52'])}; today's close is at {n['range_pos']:.0f}% of that range, {abs(n['from_high_pct']):.1f}% below the high and {n['from_low_pct']:.1f}% above the low."
                    + (" (History is still shorter than 52 weeks.)" if n["range_is_partial"] else ""))
        parts = [f"{rel(ma[k])} its {k}-day average ({_n(ma[k])})" for k in ("20", "50", "200") if ma.get(k)]
        if parts:
            hist.append("The index closed " + ", ".join(parts) + ". Moving averages describe the recent trend; they do not forecast it.")
        if n.get("similar"):
            hist.append(f"Last time {nm} closed near this level was on {slug_date(n['similar']['date'], 'en')} (around {_n(n['similar']['close'], 0)}).")
        if n.get("vol"):
            hist.append(f"Volatility over the last 20 sessions averaged {n['vol']['daily_pct']:.2f}% a day, or about {n['vol']['annual_pct']:.0f}% annualised.")
    else:
        hist.append(f"पिछले हफ़्ते, महीने, छह महीने और साल में {nm} का बदलाव {fmt('1w')}, {fmt('1m')}, {fmt('6m')} और {fmt('1y')} रहा है।")
        hist.append(f"इसकी 52 हफ़्ते की रेंज {_n(n['low52'])} से {_n(n['high52'])} है; आज का बंद भाव इस रेंज के {n['range_pos']:.0f}% पर है, यानी उच्च स्तर से {abs(n['from_high_pct']):.1f}% नीचे और निम्न स्तर से {n['from_low_pct']:.1f}% ऊपर।"
                    + (" (इतिहास अभी 52 हफ़्ते से छोटा है।)" if n["range_is_partial"] else ""))
        parts = [f"{k} दिन के औसत ({_n(ma[k])}) से {rel(ma[k])}" for k in ("20", "50", "200") if ma.get(k)]
        if parts:
            hist.append("सूचकांक " + ", ".join(parts) + " बंद हुआ। मूविंग एवरेज हाल का रुझान बताते हैं, भविष्य का अनुमान नहीं।")
        if n.get("similar"):
            hist.append(f"पिछली बार {nm} इस स्तर के आसपास {slug_date(n['similar']['date'], 'hi')} को बंद हुआ था (लगभग {_n(n['similar']['close'], 0)})।")
        if n.get("vol"):
            hist.append(f"पिछले 20 सत्रों में रोज़ का उतार-चढ़ाव औसतन {n['vol']['daily_pct']:.2f}% रहा, यानी सालाना आधार पर लगभग {n['vol']['annual_pct']:.0f}%।")

    # news (headlines are shown as given, only when they pass the filter; why-text is generic)
    items = []
    for h in news:
        if comp.check_text(h["title"], "en"):
            continue
        why = ("Included for context. Headlines like this can shift sentiment, but a single headline rarely tells the whole story."
               if en else "संदर्भ के लिए शामिल। ऐसी ख़बरें माहौल बदल सकती हैं, पर अकेली हेडलाइन पूरी कहानी कम ही बताती है।")
        items.append({"title": h["title"], "impact": "neutral", "why": why, "source": h["source"], "url": h["url"]})
        if len(items) == 5:
            break

    # point of view
    bull, bear = [], []
    ma200 = ma.get("200")
    if en:
        if ma200 and n["last"] >= ma200: bull.append(f"{nm} is above its 200-day average, which some readers take as a sign the longer trend is intact.")
        if rsi and 40 <= rsi <= 65: bull.append(f"RSI at {rsi:.0f} is in the middle zone, so the recent move does not look stretched.")
        if ch.get("6m") and ch["6m"] > 0: bull.append(f"Over six months the index is {_signed(ch['6m'])}, which shows participation has been broad enough to build gains.")
        bull.append("One optimistic reading is that steady company earnings and regular domestic investor inflows have often supported markets.")
        if ma200 and n["last"] < ma200: bear.append(f"{nm} is below its 200-day average, which some readers take as a sign the longer trend is weak.")
        if rsi and rsi >= 70: bear.append(f"RSI at {rsi:.0f} is in the 'stretched upward' zone, and markets can pause after such runs.")
        if rsi and rsi <= 30: bear.append(f"RSI at {rsi:.0f} shows heavy recent selling; weakness can persist before it eases.")
        if n["from_high_pct"] < -8: bear.append(f"The index is {abs(n['from_high_pct']):.1f}% below its 52-week high, so a lot of ground remains to be recovered.")
        bear.append("One cautious reading is that global events, higher crude oil or sharp currency moves can unsettle markets quickly.")
    else:
        if ma200 and n["last"] >= ma200: bull.append(f"{nm} अपने 200 दिन के औसत से ऊपर है, जिसे कुछ लोग लंबे रुझान के मज़बूत रहने का संकेत मानते हैं।")
        if rsi and 40 <= rsi <= 65: bull.append(f"RSI {rsi:.0f} पर बीच के क्षेत्र में है, यानी हाल की चाल ज़्यादा खिंची हुई नहीं दिखती।")
        if ch.get("6m") and ch["6m"] > 0: bull.append(f"छह महीने में सूचकांक {_signed(ch['6m'])} रहा है, जो बताता है कि बढ़त को काफ़ी लोगों का साथ मिला।")
        bull.append("उम्मीद वाला एक नज़रिया यह है कि कंपनियों की स्थिर कमाई और घरेलू निवेशकों के नियमित निवेश ने अक्सर बाज़ार को सहारा दिया है।")
        if ma200 and n["last"] < ma200: bear.append(f"{nm} अपने 200 दिन के औसत से नीचे है, जिसे कुछ लोग लंबे रुझान के कमज़ोर होने का संकेत मानते हैं।")
        if rsi and rsi >= 70: bear.append(f"RSI {rsi:.0f} पर 'ज़्यादा खिंचे हुए' क्षेत्र में है, और ऐसी तेज़ी के बाद बाज़ार थम भी सकता है।")
        if rsi and rsi <= 30: bear.append(f"RSI {rsi:.0f} हाल की भारी बिकवाली दिखाता है; कमज़ोरी थमने से पहले कुछ समय बनी रह सकती है।")
        if n["from_high_pct"] < -8: bear.append(f"सूचकांक 52 हफ़्ते के उच्च स्तर से {abs(n['from_high_pct']):.1f}% नीचे है, यानी भरपाई के लिए काफ़ी दूरी बाकी है।")
        bear.append("सावधानी वाला एक नज़रिया यह है कि वैश्विक घटनाएँ, कच्चे तेल की महँगाई या रुपये की तेज़ चाल बाज़ार को जल्दी बेचैन कर सकती हैं।")

    ma20 = ma.get("20")
    if en:
        watch = ["Global cues: how US and Asian markets open, since Indian markets often respond to them.",
                 "FII and DII flows, which the exchanges publish after the close.",
                 "Crude oil and USD/INR, which affect inflation expectations and company costs."]
        if ma20: watch.append(f"How {nm} behaves around its 20-day average ({_n(ma20)}), a short-term support/resistance reference many chart readers use.")
    else:
        watch = ["वैश्विक संकेत: अमेरिकी और एशियाई बाज़ार कैसे खुलते हैं, क्योंकि भारतीय बाज़ार अक्सर उन पर प्रतिक्रिया देता है।",
                 "FII और DII का प्रवाह, जिसे एक्सचेंज बंद होने के बाद जारी करते हैं।",
                 "कच्चा तेल और USD/INR, जो महँगाई की उम्मीदों और कंपनियों की लागत पर असर डालते हैं।"]
        if ma20: watch.append(f"{nm} अपने 20 दिन के औसत ({_n(ma20)}) के आसपास कैसा व्यवहार करता है, जिसे कई चार्ट-पाठक छोटी अवधि का सपोर्ट/रेसिस्टेंस मानते हैं।")

    return {"title": title, "summary": [s1, s2], "what_happened": what, "history": hist, "news": items,
            "pov": {"bull": bull, "bear": bear, "closing": comp.POV_CLOSING[lang]}, "watch": watch}


# ----------------------------------------------------------------------------- LLM
SYSTEM = {
    "en": """You write a friendly, easy-to-read daily blog about the Indian stock market for beginners. You are an educator, not an advisor.

HARD RULES (a program rejects any text that breaks them):
- The author is NOT a SEBI-registered investment advisor. Describe and explain; never recommend.
- NEVER say or imply buy / sell / hold / accumulate / avoid for any stock, index or asset. No price targets, no stop-losses, no entry/exit levels, no "this will go up/down", no tips, no guaranteed or certain outcomes, no ratings.
- No hype or urgency (e.g. "sure shot", "jackpot", "multibagger", "hurry"). Calm, plain tone.
- Use ONLY numbers from the FACTS. Never invent figures, causes or quotes. Say "could" / "may", never "will", about the future.
- Summarise news in your OWN words. Do not copy sentences from headlines. Explain WHY a story might matter to markets, simply.
- The point of view gives a bull case AND a bear case, as observations, never as advice. Do not write a closing sentence for it; the program adds it.
Write short sentences. Explain jargon in a few words. Output ONLY valid JSON, no markdown fences.""",
    "hi": """आप शुरुआती लोगों के लिए भारतीय शेयर बाज़ार पर रोज़ का दोस्ताना, आसान ब्लॉग लिखते हैं। आप शिक्षक हैं, सलाहकार नहीं। पूरा पाठ सरल, बोलचाल की हिन्दी (देवनागरी) में लिखें, अंग्रेज़ी से शब्दशः अनुवाद नहीं; जैसे कोई समझदार दोस्त समझा रहा हो। RSI, NIFTY जैसे नाम अंग्रेज़ी में रह सकते हैं।

सख़्त नियम (कोई प्रोग्राम इन्हें तोड़ने वाला पाठ अस्वीकार कर देता है):
- लेखक SEBI-पंजीकृत निवेश सलाहकार नहीं है। केवल बताएँ और समझाएँ; कभी सिफ़ारिश न करें।
- किसी शेयर, इंडेक्स या एसेट के लिए खरीदें / बेचें / होल्ड करें / जमा करें जैसा कुछ भी न कहें, न इशारा करें। कोई टारगेट, स्टॉप-लॉस, एंट्री/एग्ज़िट स्तर, "यह बढ़ेगा/गिरेगा", टिप, गारंटी या पक्का नतीजा नहीं।
- कोई हाइप या जल्दबाज़ी नहीं (जैसे "पक्का मुनाफ़ा", "जैकपॉट", "मल्टीबैगर")। शांत, सादा लहजा।
- केवल FACTS में दिए आँकड़े इस्तेमाल करें। आँकड़े, कारण या उद्धरण न गढ़ें। भविष्य के लिए "सकता है" / "संभव है" लिखें, "बढ़ेगा/गिरेगा" नहीं।
- ख़बरों का सार अपने शब्दों में लिखें; हेडलाइन की नक़ल न करें। सरल भाषा में समझाएँ कि ख़बर बाज़ार के लिए क्यों मायने रख सकती है।
- नज़रिए (pov) में तेज़ी का पक्ष और मंदी का पक्ष, दोनों अवलोकन के रूप में दें, सलाह के रूप में नहीं। उसका अंतिम वाक्य न लिखें; प्रोग्राम जोड़ देगा।
छोटे वाक्य लिखें। कठिन शब्द कुछ शब्दों में समझाएँ। केवल मान्य JSON दें, मार्कडाउन नहीं।""",
}

SCHEMA = """Return JSON with exactly these keys:
{"title": str (under 90 chars, plain, no hype),
 "summary": [str, str]   // "Today in one minute": exactly 2 short lines,
 "what_happened": [str, ...]  // 2-3 short paragraphs: index moves, sectors/banks/IT, gainers and losers, commodities/rupee,
 "history": [str, ...]   // 2-4 short paragraphs: where the index sits vs its 52-week range and moving averages, RSI, the 'last time near this level' date if given, 1m/6m/1y change,
 "news": [{"source_idx": int (the number of the headline), "title": str (your own short headline), "impact": "positive"|"negative"|"neutral" (market context only), "why": str (1-2 simple sentences on why it may matter to markets)}, ...]  // the 5-7 most relevant stories, fewer if fewer are relevant,
 "pov": {"bull": [str, str, str], "bear": [str, str, str]},
 "watch": [str, str, str, str]  // what to watch tomorrow, described not recommended}"""


def _user_prompt(facts: dict, news: list[dict], lang: str, feedback: list[str]) -> str:
    numbered = [{"n": i, "source": h["source"], "headline": h["title"]} for i, h in enumerate(news)]
    parts = [f"Language: {'English' if lang == 'en' else 'Hindi (Devanagari)'}", "FACTS:", json.dumps(facts, ensure_ascii=False),
             "HEADLINES (last 24h):", json.dumps(numbered, ensure_ascii=False), SCHEMA]
    if feedback:
        parts.append("YOUR PREVIOUS DRAFT WAS REJECTED. Remove or rephrase these problems, and write nothing similar:\n- " + "\n- ".join(feedback))
    return "\n\n".join(parts)


def _extract_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON object in model output")
    return json.loads(t[a:b + 1])


def _as_list(v) -> list[str]:
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v] if isinstance(v, list) else []


def normalise(raw: dict, news: list[dict], lang: str) -> dict:
    """Coerce model output into the post-content shape; map source_idx -> source + url."""
    items = []
    for it in raw.get("news", []) if isinstance(raw.get("news"), list) else []:
        try:
            src = news[int(it["source_idx"])]
        except (KeyError, ValueError, IndexError, TypeError):
            continue
        impact = it.get("impact") if it.get("impact") in ("positive", "negative", "neutral") else "neutral"
        items.append({"title": str(it.get("title", "")).strip(), "impact": impact,
                      "why": str(it.get("why", "")).strip(), "source": src["source"], "url": src["url"]})
    pov = raw.get("pov") or {}
    content = {
        "title": str(raw.get("title", "")).strip(),
        "summary": _as_list(raw.get("summary"))[:2],
        "what_happened": _as_list(raw.get("what_happened")),
        "history": _as_list(raw.get("history")),
        "news": [i for i in items if i["title"] and i["why"]][:7],
        "pov": {"bull": _as_list(pov.get("bull")), "bear": _as_list(pov.get("bear")), "closing": comp.POV_CLOSING[lang]},
        "watch": _as_list(raw.get("watch")),
    }
    required = (content["title"], len(content["summary"]) == 2, content["what_happened"], content["history"],
                content["pov"]["bull"], content["pov"]["bear"], content["watch"])
    if not all(required):
        raise ValueError("model output is missing required sections")
    return content


def anthropic_llm(api_key: str, model: str, max_tokens: int = 4500, timeout: int = 120) -> LLM:
    """Minimal Anthropic Messages API client (stdlib). The key goes only in the x-api-key header."""
    def call(system: str, user: str) -> str:
        body = json.dumps({"model": model, "max_tokens": max_tokens, "system": system,
                           "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST", headers={
            "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise LLMError(f"Anthropic HTTP {e.code}") from None
        except urllib.error.URLError as e:
            raise LLMError(f"Anthropic network error: {e.reason}") from None
        return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    return call


def llm_from_env(model: str) -> LLM | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return anthropic_llm(key, model) if key else None


def generate_content(facts: dict, news: list[dict], lang: str, llm: LLM | None) -> tuple[dict, dict]:
    """Returns (content, meta). meta: method 'llm'|'template', attempts, violations (last rejected), note."""
    meta = {"method": "template", "attempts": 0, "violations": [], "note": ""}
    if llm and news is not None:
        feedback: list[str] = []
        for attempt in range(1, MAX_TRIES + 1):
            meta["attempts"] = attempt
            try:
                content = normalise(_extract_json(llm(SYSTEM[lang], _user_prompt(facts, news, lang, feedback))), news, lang)
            except LLMError as e:
                meta["note"] = str(e)
                break  # outage / auth: no point retrying within this run
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                feedback = [f"output was not valid: {e}"]
                meta["note"] = "invalid model output"
                continue
            bad = comp.validate_post_content(content, lang)
            if not bad:
                meta.update(method="llm", violations=[], note="")
                return content, meta
            meta["violations"] = [str(v) for v in bad]
            feedback = sorted({f"{v.rule}: '{v.snippet}'" for v in bad})
        meta["note"] = meta["note"] or "model text failed compliance; used template"
    else:
        meta["note"] = "no ANTHROPIC_API_KEY; used template"
    content = template_content(facts, news, lang)
    assert not comp.validate_post_content(content, lang), "template text must always be compliant"
    return content, meta


def build_post(facts: dict, news: list[dict], llm: LLM | None) -> dict:
    post = {"date": facts["date"], "source": facts["source"], "facts": facts, "meta": {}}
    for lang in ("en", "hi"):
        post[lang], post["meta"][lang] = generate_content(facts, news, lang, llm)
    return post
