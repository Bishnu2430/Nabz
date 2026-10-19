"""The safe explanation: built only from computed values, no model involved (FR-24, ADR-0005).

Used when a value is critical, when the person hasn't consented to external AI, when the model is unavailable,
and whenever a generated explanation fails validation. It has the same shape as a generated one, so the app
renders both the same way. Hindi and Odia wording are drafts pending the native-speaker review (T2.5).
"""

from __future__ import annotations

from app.catalogue.symptoms import symptoms_for
from app.explain.payload import Payload, TestItem
from app.explain.prompt import DISCLAIMER_KEY

T = {
    "en": {
        "summary_intro": "These results are outside the lab's range:",
        "line_lab": "{test} is {value}; the lab's range is {range}.",
        "line_typical": "{test} is {value}; the typical range is {range}.",
        "sym_symptoms": " A {dir} {test} result can go along with symptoms such as {list}.",
        "sym_often_none": " A {dir} {test} result often causes no symptoms at first; it can go along with {list}.",
        "sym_none": " A {dir} {test} result usually doesn't cause symptoms.",
        "dir_low": "low", "dir_high": "high", "list_last": " or ",
        "more": "{n} more results are outside their range; you can see them on the results page.",
        "close_symptoms": "Please talk to your doctor about these results, and tell them if you notice any of these "
                          "symptoms.",
        "close": "Please talk to your doctor about these results.",
        "summary_all_in": "All {total} results are within their range. Ranges are a guide; your doctor reads them "
                          "together with your health history.",
        "summary_changes": " Some results have changed more than normal day-to-day variation since last time.",
        "summary_critical": "One or more results are far outside their range. Please contact a doctor today.",
        "low": "{test} is {value}, below the {kind} ({range}).",
        "high": "{test} is {value}, above the {kind} ({range}).",
        "normal": "{test} is {value}, within the {kind} ({range}).",
        "critical_low": "{test} is {value}, far below the {kind} ({range}). Please contact a doctor today.",
        "critical_high": "{test} is {value}, far above the {kind} ({range}). Please contact a doctor today.",
        "unknown": "{test} is {value}. The report gives no range for it.",
        "kind_lab": "lab's range", "kind_typical": "typical range",
        "change_sig": " That is {pct} % {dir} than {months} ago, more than normal day-to-day variation.",
        "change_not": " That is {pct} % {dir} than {months} ago, within normal day-to-day variation.",
        "month_one": "1 month", "months": "{n} months",
        "higher": "higher", "lower": "lower",
        "trend_rising": " It has been rising over the last {years} years.",
        "trend_falling": " It has been falling over the last {years} years.",
        "below": "below {v}", "above": "above {v}",
        "q_general": "What could explain these results?",
        "q_test": "What does my {test} result mean for me?",
        "q_repeat": "Should any of these tests be repeated, and when?",
        "q_history": "Is there anything in my health history that changes how these results are read?",
        "list_join": ", ",
        "word_usual": "{test} is {answer}, as is usual.",
        "word_other": "{test} is {answer}; usually it is {usual}.",
    },
    "hi": {
        "summary_intro": "ये परिणाम लैब की सीमा से बाहर हैं:",
        "line_lab": "{test} {value} है; लैब की सीमा {range} है।",
        "line_typical": "{test} {value} है; सामान्य सीमा {range} है।",
        "sym_symptoms": " {test} {dir} होने पर {list} जैसे लक्षण हो सकते हैं।",
        "sym_often_none": " {test} {dir} होने पर शुरुआत में अक्सर कोई लक्षण नहीं होते; बाद में {list} जैसे लक्षण हो सकते हैं।",
        "sym_none": " {test} {dir} होने पर आमतौर पर कोई लक्षण नहीं होते।",
        "dir_low": "कम", "dir_high": "अधिक", "list_last": " या ",
        "more": "{n} और परिणाम अपनी सीमा से बाहर हैं; उन्हें परिणाम पेज पर देखें।",
        "close_symptoms": "इन परिणामों के बारे में अपने डॉक्टर से बात करें, और इनमें से कोई लक्षण दिखे तो उन्हें बताएँ।",
        "close": "इन परिणामों के बारे में अपने डॉक्टर से बात करें।",
        "summary_all_in": "सभी {total} परिणाम अपनी सीमा के भीतर हैं। सीमाएँ एक मार्गदर्शक हैं; आपके डॉक्टर इन्हें आपके "
                          "स्वास्थ्य इतिहास के साथ देखते हैं।",
        "summary_changes": " पिछली बार से कुछ परिणाम सामान्य रोज़ाना बदलाव से ज़्यादा बदले हैं।",
        "summary_critical": "एक या अधिक परिणाम अपनी सीमा से बहुत बाहर हैं। कृपया आज ही डॉक्टर से संपर्क करें।",
        "low": "{test} {value} है, {kind} ({range}) से कम।",
        "high": "{test} {value} है, {kind} ({range}) से अधिक।",
        "normal": "{test} {value} है, {kind} ({range}) के भीतर।",
        "critical_low": "{test} {value} है, {kind} ({range}) से बहुत कम। कृपया आज ही डॉक्टर से संपर्क करें।",
        "critical_high": "{test} {value} है, {kind} ({range}) से बहुत अधिक। कृपया आज ही डॉक्टर से संपर्क करें।",
        "unknown": "{test} {value} है। रिपोर्ट में इसकी कोई सीमा नहीं दी गई है।",
        "kind_lab": "लैब की सीमा", "kind_typical": "सामान्य सीमा",
        "change_sig": " यह {months} पहले से {pct} % {dir} है, जो सामान्य रोज़ाना बदलाव से ज़्यादा है।",
        "change_not": " यह {months} पहले से {pct} % {dir} है, जो सामान्य रोज़ाना बदलाव के भीतर है।",
        "month_one": "1 महीने", "months": "{n} महीने",
        "higher": "अधिक", "lower": "कम",
        "trend_rising": " यह पिछले {years} वर्षों से बढ़ रहा है।",
        "trend_falling": " यह पिछले {years} वर्षों से घट रहा है।",
        "below": "{v} से कम", "above": "{v} से अधिक",
        "q_general": "इन परिणामों का क्या कारण हो सकता है?",
        "q_test": "मेरे {test} परिणाम का मेरे लिए क्या मतलब है?",
        "q_repeat": "क्या इनमें से कोई जाँच दोबारा करानी चाहिए, और कब?",
        "q_history": "क्या मेरे स्वास्थ्य इतिहास में कुछ ऐसा है जिससे इन परिणामों को पढ़ने का तरीका बदलता है?",
        "list_join": ", ",
        "word_usual": "{test}: {answer}, जैसा आमतौर पर होता है।",
        "word_other": "{test}: {answer}; आमतौर पर यह {usual} होता है।",
    },
    "or": {
        "summary_intro": "ଏହି ଫଳାଫଳଗୁଡ଼ିକ ଲ୍ୟାବର ସୀମା ବାହାରେ ଅଛି:",
        "line_lab": "{test} {value}; ଲ୍ୟାବର ସୀମା {range}।",
        "line_typical": "{test} {value}; ସାଧାରଣ ସୀମା {range}।",
        "sym_symptoms": " {test} {dir} ହେଲେ {list} ଭଳି ଲକ୍ଷଣ ଦେଖାଯାଇପାରେ।",
        "sym_often_none": " {test} {dir} ହେଲେ ଆରମ୍ଭରେ ପ୍ରାୟତଃ କୌଣସି ଲକ୍ଷଣ ଦେଖାଯାଏ ନାହିଁ; ପରେ {list} ଭଳି ଲକ୍ଷଣ ଦେଖାଯାଇପାରେ।",
        "sym_none": " {test} {dir} ହେଲେ ସାଧାରଣତଃ କୌଣସି ଲକ୍ଷଣ ଦେଖାଯାଏ ନାହିଁ।",
        "dir_low": "କମ୍", "dir_high": "ଅଧିକ", "list_last": " ବା ",
        "more": "ଆଉ {n}ଟି ଫଳାଫଳ ସୀମା ବାହାରେ ଅଛି; ଫଳାଫଳ ପୃଷ୍ଠାରେ ଦେଖନ୍ତୁ।",
        "close_symptoms": "ଏହି ଫଳାଫଳ ବିଷୟରେ ଆପଣଙ୍କ ଡାକ୍ତରଙ୍କ ସହ କଥା ହୁଅନ୍ତୁ, ଏବଂ ଏଥିମଧ୍ୟରୁ କୌଣସି ଲକ୍ଷଣ ଦେଖିଲେ ତାଙ୍କୁ ଜଣାନ୍ତୁ।",
        "close": "ଏହି ଫଳାଫଳ ବିଷୟରେ ଆପଣଙ୍କ ଡାକ୍ତରଙ୍କ ସହ କଥା ହୁଅନ୍ତୁ।",
        "summary_all_in": "ସମସ୍ତ {total}ଟି ଫଳାଫଳ ସେମାନଙ୍କ ସୀମା ମଧ୍ୟରେ ଅଛି। ସୀମା ଏକ ମାର୍ଗଦର୍ଶକ; ଆପଣଙ୍କ ଡାକ୍ତର ଏହାକୁ "
                          "ଆପଣଙ୍କ ସ୍ୱାସ୍ଥ୍ୟ ଇତିହାସ ସହ ଦେଖନ୍ତି।",
        "summary_changes": " ଗତଥର ଠାରୁ କିଛି ଫଳାଫଳ ସାଧାରଣ ଦୈନିକ ପରିବର୍ତ୍ତନଠାରୁ ଅଧିକ ବଦଳିଛି।",
        "summary_critical": "ଗୋଟିଏ ବା ଅଧିକ ଫଳାଫଳ ସୀମାଠାରୁ ବହୁତ ବାହାରେ ଅଛି। ଦୟାକରି ଆଜି ହିଁ ଡାକ୍ତରଙ୍କ ସହ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
        "low": "{test} {value}, {kind} ({range})ଠାରୁ କମ୍।",
        "high": "{test} {value}, {kind} ({range})ଠାରୁ ଅଧିକ।",
        "normal": "{test} {value}, {kind} ({range}) ମଧ୍ୟରେ।",
        "critical_low": "{test} {value}, {kind} ({range})ଠାରୁ ବହୁତ କମ୍। ଦୟାକରି ଆଜି ହିଁ ଡାକ୍ତରଙ୍କ ସହ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
        "critical_high": "{test} {value}, {kind} ({range})ଠାରୁ ବହୁତ ଅଧିକ। ଦୟାକରି ଆଜି ହିଁ ଡାକ୍ତରଙ୍କ ସହ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
        "unknown": "{test} {value}। ରିପୋର୍ଟରେ ଏହାର କୌଣସି ସୀମା ଦିଆଯାଇନାହିଁ।",
        "kind_lab": "ଲ୍ୟାବର ସୀମା", "kind_typical": "ସାଧାରଣ ସୀମା",
        "change_sig": " ଏହା {months} ପୂର୍ବଠାରୁ {pct} % {dir}, ଯାହା ସାଧାରଣ ଦୈନିକ ପରିବର୍ତ୍ତନଠାରୁ ଅଧିକ।",
        "change_not": " ଏହା {months} ପୂର୍ବଠାରୁ {pct} % {dir}, ଯାହା ସାଧାରଣ ଦୈନିକ ପରିବର୍ତ୍ତନ ମଧ୍ୟରେ।",
        "month_one": "1 ମାସ", "months": "{n} ମାସ",
        "higher": "ଅଧିକ", "lower": "କମ୍",
        "trend_rising": " ଗତ {years} ବର୍ଷ ଧରି ଏହା ବଢୁଛି।",
        "trend_falling": " ଗତ {years} ବର୍ଷ ଧରି ଏହା କମୁଛି।",
        "below": "{v}ଠାରୁ କମ୍", "above": "{v}ଠାରୁ ଅଧିକ",
        "q_general": "ଏହି ଫଳାଫଳର କାରଣ କ'ଣ ହୋଇପାରେ?",
        "q_test": "ମୋର {test} ଫଳାଫଳର ମୋ ପାଇଁ ଅର୍ଥ କ'ଣ?",
        "q_repeat": "ଏହି ପରୀକ୍ଷାଗୁଡ଼ିକ ମଧ୍ୟରୁ କୌଣସିଟି ପୁଣି କରିବା ଉଚିତ କି, ଏବଂ କେବେ?",
        "q_history": "ମୋ ସ୍ୱାସ୍ଥ୍ୟ ଇତିହାସରେ ଏପରି କିଛି ଅଛି କି ଯାହା ଏହି ଫଳାଫଳକୁ ପଢ଼ିବାର ଢଙ୍ଗ ବଦଳାଏ?",
        "list_join": ", ",
        "word_usual": "{test}: {answer}, ଯେପରି ସାଧାରଣତଃ ହୁଏ।",
        "word_other": "{test}: {answer}; ସାଧାରଣତଃ ଏହା {usual} ହୁଏ।",
    },
}

# Answers for tests reported in words (app/catalogue/qualitative.py), as said in a sentence. Hindi and Odia are drafts.
ANSWERS = {
    "en": {"absent": "absent", "trace": "present in a very small amount (trace)", "present": "present",
           "plus1": "present (+)", "plus2": "present (++)", "plus3": "present (+++)", "plus4": "present (++++)",
           "normal": "normal", "increased": "increased", "colourless": "colourless", "pale_yellow": "pale yellow",
           "yellow": "yellow", "dark_yellow": "dark yellow", "amber": "amber", "red": "red", "brown": "brown",
           "other": "an unusual colour", "clear": "clear", "slightly_turbid": "slightly cloudy", "turbid": "cloudy"},
    "hi": {"absent": "नहीं मिला", "trace": "बहुत थोड़ी मात्रा में मिला (ट्रेस)", "present": "मिला",
           "plus1": "मिला (+)", "plus2": "मिला (++)", "plus3": "मिला (+++)", "plus4": "मिला (++++)",
           "normal": "सामान्य", "increased": "बढ़ा हुआ", "colourless": "रंगहीन", "pale_yellow": "हल्का पीला",
           "yellow": "पीला", "dark_yellow": "गहरा पीला", "amber": "गहरा नारंगी-पीला", "red": "लाल", "brown": "भूरा",
           "other": "असामान्य रंग", "clear": "साफ़", "slightly_turbid": "थोड़ा धुंधला", "turbid": "धुंधला"},
    "or": {"absent": "ମିଳିଲା ନାହିଁ", "trace": "ଅତି ଅଳ୍ପ ପରିମାଣରେ ମିଳିଲା (ଟ୍ରେସ)", "present": "ମିଳିଲା",
           "plus1": "ମିଳିଲା (+)", "plus2": "ମିଳିଲା (++)", "plus3": "ମିଳିଲା (+++)", "plus4": "ମିଳିଲା (++++)",
           "normal": "ସାଧାରଣ", "increased": "ବଢ଼ିଛି", "colourless": "ରଙ୍ଗହୀନ", "pale_yellow": "ହାଲୁକା ହଳଦିଆ",
           "yellow": "ହଳଦିଆ", "dark_yellow": "ଗାଢ଼ ହଳଦିଆ", "amber": "ଗାଢ଼ କମଳା-ହଳଦିଆ", "red": "ଲାଲ", "brown": "ବାଦାମୀ",
           "other": "ଅସାଧାରଣ ରଙ୍ଗ", "clear": "ସଫା", "slightly_turbid": "ସାମାନ୍ୟ ଘୋଳିଆ", "turbid": "ଘୋଳିଆ"},
}


def _word(t: TestItem, s: dict[str, str], language: str) -> str:
    """A test reported in words: "Urine protein is present (++); usually it is absent." """
    words = ANSWERS.get(language, ANSWERS["en"])
    answer = words.get(t.answer or "", t.answer or "")
    key = "word_usual" if t.answer == t.usual or t.status == "normal" else "word_other"
    return s[key].format(test=t.test, answer=answer, usual=words.get(t.usual or "", t.usual or ""))


def fmt(v: float | int | None) -> str:
    if v is None:
        return ""
    text = f"{v}"
    return text[:-2] if text.endswith(".0") else text


def _range(t: TestItem, s: dict[str, str]) -> str:
    if t.range_low is not None and t.range_high is not None:
        return f"{fmt(t.range_low)}–{fmt(t.range_high)}"
    if t.range_high is not None:
        return s["below"].format(v=fmt(t.range_high))
    if t.range_low is not None:
        return s["above"].format(v=fmt(t.range_low))
    return ""


def _months(n: int, s: dict[str, str]) -> str:
    return s["month_one"] if n == 1 else s["months"].format(n=n)


def _sentence(t: TestItem, s: dict[str, str]) -> str:
    if t.answer is not None:
        return _word(t, s, next((lang for lang, table in T.items() if table is s), "en"))
    value = f"{fmt(t.value)} {t.unit or ''}".strip()
    kind = s["kind_lab" if t.range_source == "lab" else "kind_typical"]
    text = s[t.status].format(test=t.test, value=value, kind=kind, range=_range(t, s))
    if t.change and t.change.get("significant") is not None:
        key = "change_sig" if t.change["significant"] else "change_not"
        text += s[key].format(pct=abs(t.change["percent"]), dir=s["higher" if t.change["percent"] > 0 else "lower"],
                              months=_months(t.change["months_since_previous"], s))
    if t.trend and t.trend.get("confirmed"):
        key = "trend_rising" if t.trend["direction"] == "rising" else "trend_falling"
        text += s[key].format(years=t.trend["years"])
    return text


def _join(items: list[str], s: dict[str, str]) -> str:
    return items[0] if len(items) == 1 else s["list_join"].join(items[:-1]) + s["list_last"] + items[-1]


def _line(t: TestItem, s: dict[str, str], language: str) -> tuple[str, bool]:
    """One summary line for an out-of-range result, and whether it names symptoms."""
    if t.answer is not None:
        return _word(t, s, language), False
    value = f"{fmt(t.value)} {t.unit or ''}".strip()
    text = s["line_lab" if t.range_source == "lab" else "line_typical"].format(test=t.test, value=value,
                                                                              range=_range(t, s))
    sy = symptoms_for(t.test_code, t.status)
    if sy is None:
        return text, False
    words = list(sy.for_language(language))[:4]
    direction = s["dir_low" if t.status.endswith("low") else "dir_high"]
    text += s[f"sym_{sy.kind}"].format(dir=direction, test=t.test, list=_join(words, s) if words else "")
    return text, bool(words)


def template_explanation(payload: Payload, language: str) -> dict:
    s = T.get(language, T["en"])
    outside = [t for t in payload.focus if t.out_of_range]
    if outside:
        lines = [s["summary_critical"]] if payload.critical else []
        lines.append(s["summary_intro"])
        named = False
        for t in outside:
            line, has_symptoms = _line(t, s, language)
            lines.append("• " + line)
            named = named or has_symptoms
        if payload.outside_range > len(outside):
            lines.append(s["more"].format(n=payload.outside_range - len(outside)))
        if any(t.change and t.change.get("significant") for t in payload.focus):
            lines.append(s["summary_changes"].strip())
        lines.append(s["close_symptoms" if named else "close"])
        summary = "\n".join(lines)
    else:
        summary = s["summary_all_in"].format(total=payload.results_total)
        if any(t.change and t.change.get("significant") for t in payload.focus):
            summary += s["summary_changes"]

    questions = [s["q_general"]]
    if payload.focus:
        questions.append(s["q_test"].format(test=payload.focus[0].test))
    questions += [s["q_repeat"], s["q_history"]]
    return {
        "language": language,
        "summary": summary,
        "per_test": [{"test_code": t.test_code, "status": t.status, "what_it_measures": "",
                      "what_this_result_means": _sentence(t, s), "citations": []} for t in payload.focus],
        "doctor_questions": questions,
        "disclaimer_key": DISCLAIMER_KEY,
    }
