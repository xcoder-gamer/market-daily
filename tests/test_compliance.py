import pytest

from marketdaily import compliance as c

BAD_EN = [
    "You should buy this stock before it runs.",
    "Investors must sell now.",
    "Buy on dips.",
    "Time to accumulate banks.",
    "Set a stop-loss at 24,000.",
    "Keep a stoploss below the low.",
    "The price target is 26,000.",
    "Analysts see a target of Rs 3,000.",
    "This stock will go up tomorrow.",
    "NIFTY will definitely touch 25,000.",
    "A sure shot winner.",
    "This is a jackpot opportunity.",
    "Guaranteed returns await.",
    "Here are 5 stocks to buy today.",
    "Brokerage has a strong buy rating on it.",
    "Hot tips for Monday.",
    "Good entry level near 24,100.",
    "Hurry, last chance!",
    "Multibagger in the making.",
]
GOOD_EN = [
    "NIFTY 50 closed at 24,310, up 0.4% on the day.",
    "Foreign investors were net sellers on Friday, according to exchange data.",
    "The index is trading above its 200-day average, which some traders watch as a trend gauge.",
    "A bull case is that earnings growth stays steady; a bear case is that valuations are stretched.",
    "RSI is 62, which is in the middle zone and neither overbought nor oversold.",
    "Banks led the gains while IT lagged.",
    "Crude oil prices could affect inflation expectations.",
]
BAD_HI = [
    "इस शेयर को अभी खरीदें।",
    "आप इसे बेच दें।",
    "इसका टारगेट 26,000 है।",
    "स्टॉप लॉस 24,000 पर रखें।",
    "यह पक्का मुनाफा है।",
    "जैकपॉट मौका!",
    "निफ्टी कल बढ़ेगा।",
    "यह शेयर गिरेगा।",
    "गारंटी के साथ रिटर्न।",
    "हॉट टिप आज की।",
    "तुरंत खरीद लो।",
]
GOOD_HI = [
    "निफ्टी 50 आज 24,310 पर बंद हुआ, यानी 0.4% की बढ़त।",
    "विदेशी निवेशकों ने शुक्रवार को शेयर बेचे, एक्सचेंज के आँकड़ों के मुताबिक।",
    "सूचकांक 200 दिन के औसत से ऊपर है, जिसे कुछ ट्रेडर रुझान का पैमाना मानते हैं।",
    "तेज़ी के पक्ष में तर्क है कि कमाई स्थिर रहे; मंदी के पक्ष में तर्क है कि वैल्यूएशन महँगे हैं।",
    "कच्चे तेल की कीमतें महँगाई की उम्मीदों पर असर डाल सकती हैं।",
    "वैश्विक घटनाएँ बाज़ार को जल्दी बेचैन कर सकती हैं।",  # 'बेचैन' (uneasy) is not 'बेच' (sell)
]


@pytest.mark.parametrize("text", BAD_EN)
def test_english_violations_caught(text):
    assert c.check_text(text, "en"), text


@pytest.mark.parametrize("text", GOOD_EN)
def test_english_clean_text_passes(text):
    assert c.check_text(text, "en") == [], c.check_text(text, "en")


@pytest.mark.parametrize("text", BAD_HI)
def test_hindi_violations_caught(text):
    assert c.check_text(text, "hi"), text


@pytest.mark.parametrize("text", GOOD_HI)
def test_hindi_clean_text_passes(text):
    assert c.check_text(text, "hi") == [], c.check_text(text, "hi")


def test_hindi_nukta_variants_match():
    # same word typed with and without the nukta must both be caught
    assert c.check_text("गिरेगा", "hi") and c.check_text("बढ़ेगा", "hi") and c.check_text("बढेगा", "hi")


def test_mixed_script_hindi_still_checks_english_hype():
    assert c.check_text("यह शेयर sure shot है", "hi")


def _content(lang, closing=None, bull=True, bear=True):
    return {"pov": {"bull": ["a"] if bull else [], "bear": ["b"] if bear else [],
                    "closing": c.POV_CLOSING[lang] if closing is None else closing}}


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_pov_must_have_both_sides_and_closing(lang):
    assert c.check_pov(_content(lang), lang) == []
    assert c.check_pov(_content(lang, bear=False), lang)
    assert c.check_pov(_content(lang, bull=False), lang)
    assert c.check_pov(_content(lang, closing="Enjoy!"), lang)


def test_validate_scans_nested_prose_but_not_urls():
    content = _content("en")
    content["news"] = [{"url": "https://x.com/buy-now-guaranteed", "title": "Banks rose", "why": "Calm."}]
    assert c.validate_post_content(content, "en") == []
    content["news"][0]["why"] = "You should buy banks."
    v = c.validate_post_content(content, "en")
    assert v and "news[0].why" in v[0].where


def test_disclaimers_are_themselves_present_and_exact():
    assert "SEBI" in c.DISCLAIMER["en"] and "SEBI" in c.DISCLAIMER["hi"]
    assert "Investments are subject to market risk." in c.DISCLAIMER["en"]
    assert c.has_disclaimer("<p>" + c.DISCLAIMER["en"] + "</p>", "en")
    assert not c.has_disclaimer("<p>nothing</p>", "hi")


def test_closing_lines_are_clean():
    for lang in ("en", "hi"):
        assert c.check_text(c.POV_CLOSING[lang], lang) == []
