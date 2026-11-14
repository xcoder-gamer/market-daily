"""All user-facing copy in English and Hindi: UI labels, glossary, beginner articles, static pages."""
from __future__ import annotations

import html
import re

UI = {
    "en": {
        "lang_name": "English", "html_lang": "en", "toggle_label": "हिं", "toggle_title": "हिन्दी में पढ़ें",
        "nav": {"home": "Home", "archive": "Archive", "markets": "Markets", "learn": "Learn", "about": "About"},
        "footer_links": {"disclaimer": "Disclaimer", "privacy": "Privacy", "contact": "Contact"},
        "tagline": "Daily Indian market notes in plain language",
        "latest_post": "Latest post", "read_more": "Read the full post", "dashboard": "Market dashboard",
        "gainers": "Top NIFTY 50 gainers", "losers": "Top NIFTY 50 losers", "commodities": "Commodities & currency",
        "recent": "Recent posts", "archive_title": "Archive", "markets_title": "Markets: one-year history",
        "learn_title": "Learn: market basics for beginners", "glossary": "Glossary", "glossary_box": "Terms used in this post",
        "today_minute": "Today in one minute", "what_happened": "What happened today",
        "history": "Historical context", "news": "News that mattered", "pov": "My point of view",
        "bull": "The bull case (reasons for optimism)", "bear": "The bear case (reasons for caution)",
        "watch": "What to watch tomorrow", "source_label": "Data source", "src_upstox": "Upstox (live)",
        "src_fallback": "fallback (Yahoo Finance): primary source unavailable", "src_mock": "mock (test data)",
        "updated": "Updated", "close": "Close", "change": "Change", "ad_slot": "Ad slot (AdSense placeholder)",
        "impact": {"positive": "Market-positive context", "negative": "Market-negative context", "neutral": "Neutral context"},
        "why": "Why it may matter", "read_at": "Read at", "range52": "52-week range", "ma": "Moving averages",
        "metric": "Metric", "no_posts": "No posts yet. The first one appears after the next trading day.",
        "chart_note": "1-year closing prices. Solid line: close. Dashed: 50-day average. Dotted: 200-day average.",
        "partial": "(history shorter than 52 weeks so far)", "theme": "Theme", "subscribe": "RSS feed",
        "periods": {"1d": "1 day", "1w": "1 week", "1m": "1 month", "6m": "6 months", "1y": "1 year"},
        "from_high": "From 52w high", "from_low": "From 52w low", "volatility": "Volatility (20d, daily)",
        "skip": "Skip to content", "all_posts": "All posts",
    },
    "hi": {
        "lang_name": "हिन्दी", "html_lang": "hi", "toggle_label": "EN", "toggle_title": "Read in English",
        "nav": {"home": "होम", "archive": "आर्काइव", "markets": "बाज़ार", "learn": "सीखें", "about": "परिचय"},
        "footer_links": {"disclaimer": "अस्वीकरण", "privacy": "गोपनीयता", "contact": "संपर्क"},
        "tagline": "भारतीय बाज़ार की रोज़ की बातें, आसान भाषा में",
        "latest_post": "ताज़ा पोस्ट", "read_more": "पूरी पोस्ट पढ़ें", "dashboard": "बाज़ार डैशबोर्ड",
        "gainers": "NIFTY 50 के टॉप गेनर", "losers": "NIFTY 50 के टॉप लूज़र", "commodities": "कमोडिटी और मुद्रा",
        "recent": "हाल की पोस्ट", "archive_title": "आर्काइव", "markets_title": "बाज़ार: एक साल का इतिहास",
        "learn_title": "सीखें: शुरुआती लोगों के लिए बाज़ार की बुनियादी बातें", "glossary": "शब्दावली",
        "glossary_box": "इस पोस्ट में आए शब्द",
        "today_minute": "आज की बात, एक मिनट में", "what_happened": "आज क्या हुआ",
        "history": "पुराने आँकड़ों के साथ तुलना", "news": "ज़रूरी ख़बरें", "pov": "मेरा नज़रिया",
        "bull": "तेज़ी का पक्ष (उम्मीद के कारण)", "bear": "मंदी का पक्ष (सावधानी के कारण)",
        "watch": "कल किस पर नज़र रखें", "source_label": "डेटा स्रोत", "src_upstox": "Upstox (लाइव)",
        "src_fallback": "फ़ॉलबैक (Yahoo Finance): मुख्य स्रोत उपलब्ध नहीं था", "src_mock": "मॉक (टेस्ट डेटा)",
        "updated": "अपडेट", "close": "बंद भाव", "change": "बदलाव", "ad_slot": "विज्ञापन स्थान (AdSense प्लेसहोल्डर)",
        "impact": {"positive": "बाज़ार के लिए सकारात्मक संदर्भ", "negative": "बाज़ार के लिए नकारात्मक संदर्भ",
                   "neutral": "तटस्थ संदर्भ"},
        "why": "यह क्यों मायने रख सकता है", "read_at": "यहाँ पढ़ें", "range52": "52 हफ़्ते की रेंज",
        "ma": "मूविंग एवरेज", "metric": "पैमाना", "no_posts": "अभी कोई पोस्ट नहीं है। अगले ट्रेडिंग दिन के बाद पहली पोस्ट आएगी।",
        "chart_note": "1 साल के बंद भाव। सीधी रेखा: बंद भाव। टूटी रेखा: 50 दिन का औसत। बिंदु रेखा: 200 दिन का औसत।",
        "partial": "(अभी तक 52 हफ़्ते से कम का इतिहास)", "theme": "थीम", "subscribe": "RSS फ़ीड",
        "periods": {"1d": "1 दिन", "1w": "1 हफ़्ता", "1m": "1 महीना", "6m": "6 महीने", "1y": "1 साल"},
        "from_high": "52 हफ़्ते के उच्च से", "from_low": "52 हफ़्ते के निम्न से", "volatility": "उतार-चढ़ाव (20 दिन, रोज़ाना)",
        "skip": "मुख्य सामग्री पर जाएँ", "all_posts": "सभी पोस्ट",
    },
}

# term key -> {lang: (term, plain-language definition)}, triggers = strings that mean the term was used
GLOSSARY = {
    "rsi": {"triggers": {"en": ["RSI", "relative strength"], "hi": ["RSI"]},
            "en": ("RSI (Relative Strength Index)", "A number from 0 to 100 that compares recent gains with recent losses. Many traders read above 70 as 'stretched upward' and below 30 as 'stretched downward'. It describes recent movement; it does not predict the next move."),
            "hi": ("RSI (रिलेटिव स्ट्रेंथ इंडेक्स)", "0 से 100 के बीच का एक अंक जो हाल की बढ़त और गिरावट की तुलना करता है। 70 से ऊपर को अक्सर 'ज़्यादा खिंचा हुआ' और 30 से नीचे को 'ज़्यादा गिरा हुआ' माना जाता है। यह हाल की चाल बताता है, आगे की चाल का अनुमान नहीं।")},
    "ma": {"triggers": {"en": ["moving average", "day average", "20-day", "50-day", "200-day"], "hi": ["मूविंग एवरेज", "दिन का औसत", "दिन के औसत", "200 दिन", "50 दिन", "20 दिन"]},
           "en": ("Moving average (MA)", "The average closing price over the last N days (for example 200). It smooths out daily noise so the broader trend is easier to see."),
           "hi": ("मूविंग एवरेज (MA)", "पिछले N दिनों (जैसे 200) के बंद भावों का औसत। इससे रोज़ के उतार-चढ़ाव का शोर कम होता है और बड़ा रुझान आसानी से दिखता है।")},
    "52w": {"triggers": {"en": ["52-week", "52 week"], "hi": ["52 हफ़्ते", "52 सप्ताह", "52-हफ़्ते"]},
            "en": ("52-week high / low", "The highest and lowest prices in the last one year. It shows where today's level sits inside the past year's range."),
            "hi": ("52 हफ़्ते का उच्च / निम्न", "पिछले एक साल का सबसे ऊँचा और सबसे नीचा भाव। इससे पता चलता है कि आज का स्तर पिछले साल की रेंज में कहाँ है।")},
    "support": {"triggers": {"en": ["support", "resistance"], "hi": ["सपोर्ट", "रेसिस्टेंस"]},
                "en": ("Support and resistance", "Price areas where a market has often paused or turned before. Support is a floor-like area, resistance is a ceiling-like area. They are habits of past prices, not guarantees."),
                "hi": ("सपोर्ट और रेसिस्टेंस", "वे भाव-क्षेत्र जहाँ बाज़ार पहले अक्सर रुका या पलटा है। सपोर्ट फ़र्श जैसा और रेसिस्टेंस छत जैसा क्षेत्र है। ये पुरानी आदतें हैं, गारंटी नहीं।")},
    "volatility": {"triggers": {"en": ["volatility", "volatile"], "hi": ["उतार-चढ़ाव", "वोलैटिलिटी"]},
                   "en": ("Volatility", "How much prices swing up and down. Here it is the standard deviation of the last 20 daily percentage moves. Higher means bigger daily swings."),
                   "hi": ("वोलैटिलिटी (उतार-चढ़ाव)", "कीमतें कितना ऊपर-नीचे होती हैं। यहाँ यह पिछले 20 दिनों की रोज़ की प्रतिशत चाल का मानक विचलन है। ज़्यादा मतलब रोज़ बड़े झटके।")},
    "gainers": {"triggers": {"en": ["gainers", "losers"], "hi": ["गेनर", "लूज़र", "लूजर"]},
                "en": ("Gainers and losers", "Stocks that rose the most (gainers) or fell the most (losers) on the day, as a percentage change from the previous close."),
                "hi": ("गेनर और लूज़र", "दिन में सबसे ज़्यादा चढ़ने वाले (गेनर) और सबसे ज़्यादा गिरने वाले (लूज़र) शेयर, पिछले बंद भाव से प्रतिशत बदलाव के हिसाब से।")},
    "nifty": {"triggers": {"en": ["NIFTY 50", "NIFTY"], "hi": ["NIFTY", "निफ्टी"]},
              "en": ("NIFTY 50", "An index of 50 large companies listed on the National Stock Exchange. It is a quick way to see how the big-company part of the market is doing."),
              "hi": ("NIFTY 50", "नेशनल स्टॉक एक्सचेंज में लिस्टेड 50 बड़ी कंपनियों का सूचकांक। इससे बड़ी कंपनियों वाले बाज़ार का हाल एक नज़र में दिखता है।")},
    "sensex": {"triggers": {"en": ["SENSEX"], "hi": ["SENSEX", "सेंसेक्स"]},
               "en": ("SENSEX", "An index of 30 large companies listed on the BSE (Bombay Stock Exchange)."),
               "hi": ("SENSEX", "BSE (बॉम्बे स्टॉक एक्सचेंज) में लिस्टेड 30 बड़ी कंपनियों का सूचकांक।")},
    "banknifty": {"triggers": {"en": ["BANK NIFTY"], "hi": ["BANK NIFTY", "बैंक निफ्टी"]},
                  "en": ("BANK NIFTY", "An index of the most traded banking stocks on the NSE."),
                  "hi": ("BANK NIFTY", "NSE के सबसे ज़्यादा कारोबार वाले बैंकिंग शेयरों का सूचकांक।")},
    "fii": {"triggers": {"en": ["FII", "DII", "foreign investors", "institutional"], "hi": ["FII", "DII", "विदेशी निवेशक"]},
            "en": ("FII and DII", "Foreign Institutional Investors (FII) and Domestic Institutional Investors (DII), such as mutual funds and insurers. Their buying and selling can move the market, and their daily numbers are published by the exchanges."),
            "hi": ("FII और DII", "विदेशी संस्थागत निवेशक (FII) और घरेलू संस्थागत निवेशक (DII), जैसे म्यूचुअल फ़ंड और बीमा कंपनियाँ। इनकी खरीद-बिक्री से बाज़ार हिल सकता है; इनके रोज़ के आँकड़े एक्सचेंज जारी करते हैं।")},
    "usdinr": {"triggers": {"en": ["USD/INR", "rupee"], "hi": ["USD/INR", "रुपया", "रुपये"]},
               "en": ("USD/INR", "How many rupees one US dollar costs. A weaker rupee makes imports (like oil) costlier."),
               "hi": ("USD/INR", "एक अमेरिकी डॉलर की कीमत कितने रुपये है। रुपया कमज़ोर हो तो आयात (जैसे तेल) महँगा पड़ता है।")},
    "crude": {"triggers": {"en": ["crude"], "hi": ["कच्चा तेल", "कच्चे तेल", "क्रूड"]},
              "en": ("Crude oil", "Unrefined oil. India imports most of its oil, so crude prices influence inflation, the rupee and company costs."),
              "hi": ("क्रूड ऑयल (कच्चा तेल)", "बिना साफ़ किया तेल। भारत अपना ज़्यादातर तेल आयात करता है, इसलिए इसकी कीमत महँगाई, रुपये और कंपनियों की लागत पर असर डालती है।")},
    "bullbear": {"triggers": {"en": ["bull case", "bear case", "bullish", "bearish"], "hi": ["तेज़ी का पक्ष", "मंदी का पक्ष"]},
                 "en": ("Bull case / bear case", "A bull case lists reasons markets could do well; a bear case lists reasons for caution. Looking at both helps avoid one-sided thinking."),
                 "hi": ("बुल केस / बेयर केस", "बुल केस में वे कारण होते हैं जिनसे बाज़ार अच्छा कर सकता है; बेयर केस में सावधानी के कारण। दोनों देखने से एकतरफ़ा सोच से बचाव होता है।")},
}


def glossary_for(text: str, lang: str) -> list[tuple[str, str]]:
    """Glossary entries whose trigger words appear in `text`."""
    out = []
    for g in GLOSSARY.values():
        if any(t.lower() in text.lower() for t in g["triggers"][lang]):
            out.append(g[lang])
    return out


def all_glossary(lang: str) -> list[tuple[str, str]]:
    return [g[lang] for g in GLOSSARY.values()]


ARTICLES = {
    "en": [
        ("What is a stock market index?", ["An index is a basket of shares that tracks how a part of the market is doing. NIFTY 50 follows 50 large companies on the NSE; SENSEX follows 30 on the BSE.", "When people say 'the market is up', they usually mean an index like these rose. It is a summary, not every stock: on an 'up' day many individual shares can still fall."]),
        ("How to read a 52-week range", ["The 52-week high and low are the best and worst prices of the past year. Where today's price sits between them (near the top, middle or bottom) gives a quick sense of context.", "A price near the top of its range is not automatically 'expensive' and one near the bottom is not automatically 'cheap'. The range only tells you where it has been."]),
        ("Moving averages in plain words", ["A 200-day moving average is the average of the last 200 closing prices. Because it changes slowly, it shows the long-term direction without daily noise.", "People often compare today's price with the 50-day and 200-day averages to describe the trend. It describes the past; it does not forecast."]),
        ("Why news moves markets", ["Markets are made of people's expectations about the future. News about interest rates, inflation, oil prices or company earnings can change those expectations.", "A single headline rarely tells the full story, which is why these posts always explain the context and show both a bull case and a bear case."]),
    ],
    "hi": [
        ("शेयर बाज़ार का इंडेक्स क्या होता है?", ["इंडेक्स शेयरों की एक टोकरी है जो बताती है कि बाज़ार का एक हिस्सा कैसा चल रहा है। NIFTY 50 NSE की 50 बड़ी कंपनियों को और SENSEX BSE की 30 बड़ी कंपनियों को ट्रैक करता है।", "जब लोग कहते हैं 'बाज़ार चढ़ा', तो अक्सर मतलब ऐसे ही किसी इंडेक्स के बढ़ने से होता है। यह सारांश है, हर शेयर नहीं: 'तेज़ी' वाले दिन भी कई शेयर गिर सकते हैं।"]),
        ("52 हफ़्ते की रेंज कैसे पढ़ें", ["52 हफ़्ते का उच्च और निम्न पिछले एक साल के सबसे ऊँचे और सबसे नीचे भाव होते हैं। आज का भाव इनके बीच कहाँ है (ऊपर, बीच में या नीचे), इससे संदर्भ का अंदाज़ा मिलता है।", "रेंज के ऊपर वाला भाव अपने आप 'महँगा' नहीं हो जाता और नीचे वाला अपने आप 'सस्ता' नहीं। रेंज सिर्फ़ यह बताती है कि भाव कहाँ-कहाँ रहा है।"]),
        ("मूविंग एवरेज आसान भाषा में", ["200 दिन का मूविंग एवरेज पिछले 200 बंद भावों का औसत है। यह धीरे बदलता है, इसलिए रोज़ के शोर के बिना लंबे समय की दिशा दिखाता है।", "लोग अक्सर आज के भाव की तुलना 50 और 200 दिन के औसत से करके रुझान समझाते हैं। यह बीते समय का हाल बताता है, भविष्यवाणी नहीं करता।"]),
        ("ख़बरों से बाज़ार क्यों हिलता है", ["बाज़ार भविष्य को लेकर लोगों की उम्मीदों से बनता है। ब्याज दर, महँगाई, तेल की कीमत या कंपनियों की कमाई की ख़बरें इन उम्मीदों को बदल सकती हैं।", "एक हेडलाइन पूरी कहानी कम ही बताती है, इसीलिए इन पोस्ट में संदर्भ समझाया जाता है और तेज़ी व मंदी, दोनों पक्ष दिखाए जाते हैं।"]),
    ],
}

PAGES = {
    "en": {
        "about": ("About", [
            "Market Daily is a small, independent project that explains what happened in the Indian stock market each trading day, in plain language, with history for context.",
            "Every post follows the same shape: what happened, how today compares with the past, which news mattered and why, a balanced point of view (bull case and bear case), and what to watch next.",
            "The numbers come from exchange data through the Upstox API (with Yahoo Finance as a backup). News summaries are written in our own words with links to the original sources. Parts of the text are drafted with the help of an AI model and checked by automated rules that block any buy/sell advice.",
            "The author is not a SEBI-registered investment advisor. This site is for education only.",
        ]),
        "disclaimer": ("Disclaimer", [
            "This is my personal point of view for education only. I am not a SEBI-registered investment advisor. Do your own research and analysis, and decide on your own before any purchase. Investments are subject to market risk.",
            "Nothing on this website is a recommendation to buy, sell or hold any security, and nothing here is a price target, a stop-loss or a tip. Descriptions of past prices, averages and indicators explain what has happened; they do not predict what will happen.",
            "Data may be delayed, incomplete or wrong. Text is partly generated with an AI model and may contain mistakes. The author accepts no liability for any decision taken using this website. Past performance does not guarantee future results.",
        ]),
        "privacy": ("Privacy policy", [
            "This site does not ask you to create an account and does not collect personal data itself. Your language and theme choices are stored only in your own browser (localStorage) and are never sent to us.",
            "If advertising (such as Google AdSense) or analytics is added later, those services may use cookies. This page will be updated first, and where required a consent choice will be shown.",
            "If you email us, we use your address only to reply. We do not sell or share it.",
        ]),
        "contact": ("Contact", ["For corrections, feedback or questions, please write to the email below. We cannot give personal investment advice."]),
        "learn_intro": "Short explainers for beginners, then a glossary of every term used in the posts.",
    },
    "hi": {
        "about": ("परिचय", [
            "Market Daily एक छोटा, स्वतंत्र प्रोजेक्ट है जो हर ट्रेडिंग दिन भारतीय शेयर बाज़ार में क्या हुआ, यह आसान भाषा में और पुराने आँकड़ों के संदर्भ के साथ समझाता है।",
            "हर पोस्ट का ढाँचा एक जैसा है: आज क्या हुआ, आज की तुलना बीते समय से, कौन-सी ख़बरें क्यों मायने रखती हैं, संतुलित नज़रिया (तेज़ी और मंदी, दोनों पक्ष), और आगे किस पर नज़र रखें।",
            "आँकड़े Upstox API से एक्सचेंज डेटा के रूप में आते हैं (बैकअप के तौर पर Yahoo Finance)। ख़बरों का सार हमारे अपने शब्दों में लिखा जाता है और मूल स्रोत का लिंक दिया जाता है। पाठ का कुछ हिस्सा AI मॉडल की मदद से तैयार होता है और स्वचालित नियम किसी भी खरीद-बिक्री की सलाह को रोकते हैं।",
            "लेखक SEBI-पंजीकृत निवेश सलाहकार नहीं है। यह साइट केवल शिक्षा के लिए है।",
        ]),
        "disclaimer": ("अस्वीकरण", [
            "यह केवल शिक्षा के उद्देश्य से मेरा निजी दृष्टिकोण है। मैं SEBI-पंजीकृत निवेश सलाहकार नहीं हूँ। अपना शोध और विश्लेषण खुद करें, और कोई भी खरीदारी करने से पहले अपना निर्णय खुद लें। निवेश बाज़ार जोखिमों के अधीन हैं।",
            "इस वेबसाइट पर कुछ भी किसी सिक्योरिटी को खरीदने, बेचने या रखने की सिफ़ारिश नहीं है, और न ही कोई प्राइस टारगेट, स्टॉप-लॉस या टिप है। पुराने भाव, औसत और संकेतकों का वर्णन यह समझाता है कि क्या हो चुका है; यह नहीं बताता कि आगे क्या होगा।",
            "डेटा देर से, अधूरा या ग़लत हो सकता है। पाठ का कुछ हिस्सा AI मॉडल से बनता है और उसमें ग़लतियाँ हो सकती हैं। इस वेबसाइट के आधार पर लिए गए किसी भी निर्णय की ज़िम्मेदारी लेखक की नहीं है। बीता प्रदर्शन भविष्य के नतीजों की गारंटी नहीं है।",
        ]),
        "privacy": ("गोपनीयता नीति", [
            "यह साइट आपसे खाता बनाने को नहीं कहती और स्वयं कोई निजी डेटा इकट्ठा नहीं करती। आपकी भाषा और थीम की पसंद सिर्फ़ आपके अपने ब्राउज़र (localStorage) में रहती है, हमें नहीं भेजी जाती।",
            "यदि बाद में विज्ञापन (जैसे Google AdSense) या एनालिटिक्स जोड़े गए, तो वे कुकीज़ का उपयोग कर सकते हैं। पहले यह पेज अपडेट होगा, और ज़रूरत पड़ने पर सहमति का विकल्प दिखाया जाएगा।",
            "यदि आप हमें ईमेल करते हैं, तो आपका पता सिर्फ़ जवाब देने के लिए इस्तेमाल होगा। हम इसे बेचते या साझा नहीं करते।",
        ]),
        "contact": ("संपर्क", ["सुधार, सुझाव या सवालों के लिए नीचे दिए ईमेल पर लिखें। हम व्यक्तिगत निवेश सलाह नहीं दे सकते।"]),
        "learn_intro": "शुरुआती लोगों के लिए छोटे लेख, और फिर पोस्ट में आने वाले हर शब्द की शब्दावली।",
    },
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def slug_date(date: str, lang: str) -> str:
    """'2026-11-13' -> '13 Nov 2026' / '13 नवंबर 2026'."""
    import datetime as dt
    d = dt.date.fromisoformat(date)
    months_hi = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
    if lang == "hi":
        return f"{d.day} {months_hi[d.month - 1]} {d.year}"
    return d.strftime("%d %b %Y").lstrip("0")


_ = re  # keep import for callers that extend this module
