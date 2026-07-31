"""Speech generation for VeldWys.

The hard problem is Oshiwambo and Otjiherero. No TTS engine ships native voices for
them, and left alone the models read "53" and "N$1,500" in English in the middle of an
Oshiwambo sentence, which is exactly what a native speaker notices first.

So speech runs in two stages:

  1. PREP  - a cheap text pass that rewrites the sentence the way it should be *said*:
             numbers, money and dates spelled out as native words, units expanded.
  2. SPEAK - the TTS model, told which language and accent it is reading.

Stage 1 is cached, so repeat lines (dashboard alerts, briefings) cost nothing.
OVERRIDES holds hand-checked native spellings that the prep pass must not change.
"""
import re
from typing import Dict

import numerals

LANG_NAMES = {"en": "English", "af": "Afrikaans", "ng": "Oshiwambo", "kj": "Otjiherero"}

# Voice choices, picked for warmth rather than newsreader polish.
VOICES = {
    "female": {"en": "nova", "af": "nova", "ng": "shimmer", "kj": "shimmer"},
    "male": {"en": "onyx", "af": "onyx", "ng": "ash", "kj": "ash"},
}

# Hand-verified spellings the prep pass must reuse verbatim. Teo (native speaker)
# corrects these after listening; whatever lands here wins over the model's guess.
OVERRIDES: Dict[str, Dict[str, str]] = {
    "ng": {
        "N$": "oodola dhaNamibia",
        "mm": "omilimita",
        "ha": "oohekitali",
        "LSU": "oiyuunga yoimuna",
    },
    "kj": {
        "N$": "ozondora zoNamibia",
        "mm": "ozomilimeta",
        "ha": "ozohekitare",
        "LSU": "ovinamuinyo ovinene",
    },
    "af": {
        "N$": "Namibiese dollar",
        "mm": "millimeter",
        "ha": "hektaar",
        "LSU": "grootvee-eenhede",
    },
    "en": {
        "N$": "Namibian dollars",
        "mm": "millimetres",
        "ha": "hectares",
        "LSU": "large stock units",
    },
}

ACCENT = {
    "en": ("Namibian English. Warm, unhurried but not slow, like a farmer talking to a neighbour "
           "over a fence. Southern African vowels, not American."),
    "af": ("Namibian Afrikaans. A real Afrikaans accent, rolled r, crisp g, the way it is spoken in "
           "Windhoek and on the farms around Gobabis. Never read it with an English accent."),
    "ng": ("Oshiwambo, a Bantu language of northern Namibia. Syllable-timed with even rhythm, every "
           "syllable given its full value. Pure clean vowels a e i o u as in Spanish or Italian, never "
           "English diphthongs. Consonants crisp, sh and mb and nd and ng pronounced fully. Words end "
           "in vowels, so never clip the final vowel. Read every word as Oshiwambo, including numbers "
           "and names. Do not switch to an English accent at any point."),
    "kj": ("Otjiherero, a Bantu language of central Namibia. Syllable-timed, even and flowing, each "
           "syllable clear. Pure vowels a e i o u as in Italian, never English diphthongs. The tj is a "
           "soft ch, the mb nd ng are pronounced as full clusters, and the letter j is a y sound. Words "
           "end in vowels, never clip them. Read every word including numbers as Otjiherero, and never "
           "drift into an English accent."),
}

def voice_for(lang: str, gender: str) -> str:
    return VOICES.get(gender, VOICES["female"]).get(lang, "nova")


def needs_prep(text: str) -> bool:
    """Only pay for the prep call when there is actually something to convert."""
    return bool(re.search(r"\d|N\$|%|\bmm\b|\bha\b|\bLSU\b|\bkg\b", text))


MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "af": ["Januarie", "Februarie", "Maart", "April", "Mei", "Junie", "Julie",
           "Augustus", "September", "Oktober", "November", "Desember"],
    "ng": ["Januali", "Februali", "Match", "Apilili", "Mei", "Juni", "Juli",
           "Auguste", "Septemba", "Oktoba", "Novemba", "Desemba"],
    "kj": ["Januari", "Februari", "Marise", "Apriri", "Meye", "Juni", "Juli",
           "Auguste", "Septemba", "Oktoba", "Novemba", "Desemba"],
}


async def prepare_speech(client, text: str, lang: str) -> str:
    """Turn written text into words that can be spoken aloud in `lang`.

    This is deliberately deterministic. The agent already replies *in* the farmer's
    language, so nothing needs translating here, only digits and symbols need to
    become words. An earlier LLM version of this invented Oshiwambo words and looped
    forever on Otjiherero, so the number system lives in numerals.py instead.
    """
    out = re.sub(r"[*_`#]+", "", text or "").strip()
    if not out:
        return ""

    # Dates first, so 2026-07-22 doesn't get eaten by the plain-number rule.
    def _date(m):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        month = MONTHS.get(lang, MONTHS["en"])[mo - 1]
        return f"{numerals.number_to_words(d, lang)} {month} {numerals.number_to_words(y, lang)}"
    out = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", _date, out)

    # Money: "N$1,500" -> "one thousand five hundred Namibian dollars"
    money_word = OVERRIDES.get(lang, OVERRIDES["en"])["N$"]
    def _money(m):
        amount = m.group(1).replace(",", "").replace(" ", "")
        if "." in amount:
            whole, frac = amount.split(".", 1)
            spoken = numerals.decimal_to_words(int(whole or 0), frac, lang)
        else:
            spoken = numerals.number_to_words(int(amount or 0), lang)
        return f"{spoken} {money_word}"
    out = re.sub(r"N\$\s*([\d][\d,]*(?:\.\d+)?)", _money, out)
    out = re.sub(r"([a-zA-Z])(?=[A-Z][a-z])", r"\1 ", out)   # guard against run-on words

    # Units attached to a number: 3.4 mm, 1800 ha, 58.5 LSU, 12 kg
    for unit, word in (("mm", OVERRIDES.get(lang, OVERRIDES["en"])["mm"]),
                       ("ha", OVERRIDES.get(lang, OVERRIDES["en"])["ha"]),
                       ("LSU", OVERRIDES.get(lang, OVERRIDES["en"])["LSU"]),
                       ("kg", {"af": "kilogram", "ng": "ookilograma",
                               "kj": "ozokilograma"}.get(lang, "kilograms"))):
        out = re.sub(rf"(\d[\d.,]*)\s*{unit}\b", rf"\1 {word}", out)

    percent = {"af": "persent", "ng": "opelesenda", "kj": "opersende"}.get(lang, "percent")
    out = re.sub(r"(\d[\d.,]*)\s*%", rf"\1 {percent}", out)

    # Finally every remaining number becomes words in the target language.
    def _num(m):
        raw = m.group(0).replace(",", "")
        if "." in raw:
            whole, frac = raw.split(".", 1)
            return numerals.decimal_to_words(int(whole or 0), frac, lang)
        return numerals.number_to_words(int(raw), lang)
    out = re.sub(r"\b\d[\d,]*(?:\.\d+)?\b", _num, out)

    return re.sub(r"\s{2,}", " ", out).strip()


def speak_instructions(lang: str, speed: float = 1.0) -> str:
    pace = "Speak briskly and naturally, at the pace of ordinary conversation, never slow or lecturing."
    if speed >= 1.15:
        pace = "Speak quickly and energetically, like someone in a hurry to share good news."
    elif speed <= 0.9:
        pace = "Speak calmly and clearly, a little slower than usual, but never draggy."
    return (
        f"{ACCENT.get(lang, ACCENT['en'])}\n{pace}\n"
        "You are speaking to a livestock farmer in Namibia. Sound like a real person who knows them, "
        "warm and direct. Do not sound like a news reader or an automated system."
    )
