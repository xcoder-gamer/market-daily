"""Compliance filter. The author is NOT a SEBI-registered investment advisor, so generated text may
describe and explain but never recommend. Used (1) in the LLM prompt, (2) as a post-generation gate
that rejects text so it can be regenerated, and (3) on every template/script we write ourselves."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

DISCLAIMER = {
    "en": ("This is my personal point of view for education only. I am not a SEBI-registered "
           "investment advisor. Do your own research and analysis, and decide on your own before "
           "any purchase. Investments are subject to market risk."),
    "hi": ("यह केवल शिक्षा के उद्देश्य से मेरा निजी दृष्टिकोण है। मैं SEBI-पंजीकृत निवेश सलाहकार नहीं हूँ। "
           "अपना शोध और विश्लेषण खुद करें, और कोई भी खरीदारी करने से पहले अपना निर्णय खुद लें। "
           "निवेश बाज़ार जोखिमों के अधीन हैं।"),
}

# The "My point of view" section must always END with this.
POV_CLOSING = {
    "en": "These are only observations, not advice. Please do your own analysis before making any decision.",
    "hi": "ये केवल मेरे अवलोकन हैं, सलाह नहीं। कोई भी निर्णय लेने से पहले कृपया अपना विश्लेषण खुद करें।",
}


def _n(s: str) -> str:
    """Normalise Devanagari: NFC and drop the nukta so ज़/ज and ढ़/ढ match either way."""
    return unicodedata.normalize("NFC", s).replace("़", "")


_EN_VERBS = r"(?:buy|sell|hold|accumulate|short|book\s+profits?|average\s+(?:down|out)|add\s+more|load\s+up)"
_EN = [
    ("advice-verb", rf"\b(?:should|must|ought\s+to|need\s+to|needs\s+to|better\s+to|advise\s+to|recommend|suggest|"
                    rf"time\s+to|go\s+ahead\s+and|can\s+(?:safely\s+)?|could|may\s+want\s+to|consider|try\s+to|let'?s)\s+"
                    rf"(?:also\s+|now\s+|only\s+)?{_EN_VERBS}\b"),
    ("imperative", rf"(?:^|[.!?:;]\s+|\n)\s*(?:buy|sell|accumulate|book\s+profits?|exit|avoid|invest)\b"),
    ("action-phrase", r"\b(?:buy|sell|hold|accumulate)\s+(?:on\s+dips?|on\s+decline|now|today|this|these|the\s+stock|"
                      r"shares?|it\b|more|aggressively)"),
    ("call-or-rating", r"\b(?:strong\s+|top\s+|best\s+)?(?:buy|sell|hold|accumulate)\s+(?:rating|call|signal|recommendation)\b"),
    ("stock-picks", r"\b(?:stocks?|shares?|picks?|ideas?)\s+to\s+(?:buy|sell|bet|invest|accumulate|avoid)\b"),
    ("price-target", r"\b(?:price\s+target|target\s+price|targets?\s+(?:of\s+|at\s+)?(?:rs\.?\s*|₹|\$|\d)|"
                     r"upside\s+target|downside\s+target)"),
    ("stop-loss", r"\bstop[\s-]*loss(?:es)?\b|\bSL\s+(?:at|of)\b"),
    ("entry-exit-level", r"\b(?:entry|exit)\s+(?:point|level|price|zone)\b"),
    ("certain-future", r"\b(?:will|is\s+going\s+to|is\s+sure\s+to|bound\s+to|set\s+to)\s+(?:definitely\s+|surely\s+|certainly\s+)?"
                       r"(?:go\s+up|go\s+down|rise|surge|rally|shoot\s+up|double|triple|crash|fall|drop|plunge|jump|soar|"
                       r"break\s+out|breakout|touch|reach|hit|cross|zoom)\b"),
    ("hype", r"\b(?:sure[\s-]*shot|jackpot|guarantee[ds]?|risk[\s-]*free|multi[\s-]*bagger|can'?t\s+miss|don'?t\s+miss|"
             r"hot\s+tips?|stock\s+tips?|trading\s+tips?|insider|rocket|moonshot|to\s+the\s+moon|bonanza|get\s+rich|"
             r"easy\s+money|assured\s+returns?|100\s*%\s*(?:safe|sure|return|profit)|act\s+now|hurry|last\s+chance|"
             r"once[\s-]*in[\s-]*a[\s-]*lifetime|fomo|explosive\s+(?:gains?|returns?))\b"),
    ("profit-promise", r"\byou\s+(?:will|can|could)\s+(?:definitely\s+)?(?:make|earn|get)\s+(?:big\s+)?(?:profits?|money|returns?)\b"),
]

_HI = [
    ("buy-sell-verb", r"(?:खरीद(?:ें|िए|ो|\s*लें|\s*लीजिए|ना\s+चाहिए|नी\s+चाहिए)|"
                      r"बेच(?:ें|िए|ो|\s*दें|\s*दीजिए|ना\s+चाहिए)|"
                      r"होल्ड\s*(?:करें|करो|कीजिए|रखें)|एक्युमुलेट|जमा\s+करें)"),
    ("urgent-action", r"(?:तुरंत|अभी|आज\s+ही|जल्दी)\s*(?:खरीद|बेच(?!ैन)|निवेश)"),
    ("price-target", r"(?:टारगेट|लक्ष्य\s*(?:मूल्य|कीमत)|प्राइस\s*टारगेट)"),
    ("stop-loss", r"स्टॉप[\s-]*लॉस|स्टॉपलॉस|एसएल\s*(?:पर|लगाएं)"),
    ("call-or-rating", r"(?:बाय|सेल|होल्ड)\s*(?:रेटिंग|कॉल|सिग्नल)|खरीदने\s+लायक|बेचने\s+लायक"),
    ("hype", r"(?:पक्का\s*(?:मुनाफ़ा|मुनाफा|फायदा|रिटर्न)|गारंटी|गारंटीशुदा|जैकपॉट|धमाका|रॉकेट|मालामाल|"
             r"अमीर\s*बन|सुनिश्चित\s*(?:मुनाफ़ा|रिटर्न)|बिना\s*जोखिम|रिस्क[\s-]*फ्री|मल्टीबैगर|सुपरहिट\s*शेयर|हॉट\s*टिप|"
             r"स्टॉक\s*टिप|शेयर\s*टिप|मौका\s*मत\s*चूक|आखिरी\s*मौका)"),
    ("certain-future", r"(?:बढ़ेगा|बढ़ेगी|चढ़ेगा|चढ़ेगी|उछलेगा|उछलेगी|गिरेगा|गिरेगी|टूटेगा|टूटेगी|दोगुना\s*होगा|"
                       r"छूएगा|छुएगा|पार\s*करेगा|पहुँचेगा|पहुंचेगा)"),
]

_RULES = {
    "en": [(name, re.compile(pat, re.IGNORECASE)) for name, pat in _EN],
    "hi": [(name, re.compile(_n(pat))) for name, pat in _HI],
}
# English terms also appear inside Hindi text (Latin script), so check those rules there too.
_RULES["hi"] += [(name, rx) for name, rx in _RULES["en"] if name in ("hype", "stop-loss", "price-target", "stock-picks")]


@dataclass(frozen=True)
class Violation:
    rule: str
    snippet: str
    where: str = ""

    def __str__(self) -> str:
        loc = f" [{self.where}]" if self.where else ""
        return f"{self.rule}: '{self.snippet}'{loc}"


def check_text(text: str, lang: str, where: str = "") -> list[Violation]:
    if not text:
        return []
    text = _n(text) if lang == "hi" else text
    out = []
    for name, rx in _RULES[lang]:
        for m in rx.finditer(text):
            out.append(Violation(name, m.group(0).strip(), where))
    return out


def iter_strings(obj, path: str = ""):
    """Yield (path, string) for every string inside nested dict/list content."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


# fields that hold URLs / ids / enums rather than prose
_SKIP_KEYS = {"url", "source", "impact", "idx", "term", "terms", "lang", "date", "key"}


def check_content(content: dict, lang: str) -> list[Violation]:
    """Scan every prose field of one language's post content."""
    out: list[Violation] = []
    for path, s in iter_strings(content):
        if path.split(".")[-1].split("[")[0] in _SKIP_KEYS:
            continue
        out.extend(check_text(s, lang, path))
    return out


def check_pov(content: dict, lang: str) -> list[Violation]:
    """Structural rules for the point-of-view section."""
    pov = content.get("pov") or {}
    out = []
    if not pov.get("bull") or not pov.get("bear"):
        out.append(Violation("pov-needs-both-sides", "bull/bear missing", "pov"))
    if pov.get("closing", "").strip() != POV_CLOSING[lang]:
        out.append(Violation("pov-must-end-with-own-analysis", str(pov.get("closing", ""))[:60], "pov.closing"))
    return out


def validate_post_content(content: dict, lang: str) -> list[Violation]:
    return check_content(content, lang) + check_pov(content, lang)


def has_disclaimer(html_or_text: str, lang: str) -> bool:
    return DISCLAIMER[lang] in html_or_text.replace("&amp;", "&")
