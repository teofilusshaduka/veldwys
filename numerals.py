"""Number-to-words for the languages VeldWys speaks.

Why this exists: asking an LLM to write Oshiwambo or Otjiherero numerals produces
nonsense (it invents words, and for Otjiherero it degenerates into repetition). The
number systems in both languages are regular and documented, so we build them properly
in code instead. Deterministic, instant, free, and correctable by a native speaker.

Both languages build numbers the same way:
    tens unit                 53  ->  "fifty" + link + "three"
    hundreds ... thousands    with a linking word between parts

NATIVE SPEAKER: everything you might want to correct is in the tables below.
Change a word here and every spoken number in the app changes with it.
"""
from typing import Dict, List

# ── Oshiwambo (Oshindonga) ───────────────────────────────────────────────────
NG = {
    "units": ["", "gumwe", "yaali", "yatatu", "yane", "yatano",
              "yahamano", "yaheyali", "yahetatu", "yomugoyi"],
    "ten": "omulongo",
    "tens": ["", "omulongo", "omilongo mbali", "omilongo ntatu", "omilongo ne",
             "omilongo ntano", "omilongo hamano", "omilongo heyali",
             "omilongo hetatu", "omilongo omugoyi"],
    "hundred": "ethele", "hundreds": "omathele",
    "thousand": "eyuvi", "thousands": "omayuvi",
    # "oshimwe inaashi kala" was not a word for zero. Namibian speakers say nulu, and
    # a decimal point is read komma, as in Afrikaans.
    "and": "na", "zero": "nulu", "point": "komma",
}

# ── Oshiwambo (Oshikwanyama) ─────────────────────────────────────────────────
# Same counting system as Oshindonga, different concords and a few different stems.
KJ = {
    "units": ["", "umwe", "vali", "vatatu", "vane", "vatano",
              "vahamano", "vaheyali", "vahetatu", "vomugoi"],
    "ten": "omulongo",
    "tens": ["", "omulongo", "omilongo ivali", "omilongo itatu", "omilongo ine",
             "omilongo itano", "omilongo ihamano", "omilongo iheyali",
             "omilongo ihetatu", "omilongo omugoi"],
    "hundred": "efele", "hundreds": "omafele",
    "thousand": "eyovi", "thousands": "omayovi",
    "and": "na", "zero": "nulu", "point": "komma",
}

# ── Otjiherero ───────────────────────────────────────────────────────────────
HZ = {
    "units": ["", "imwe", "mbari", "ndatu", "ine", "ndano",
              "hamboumwe", "hambombari", "hambondatu", "muvyu"],
    "ten": "omurongo",
    "tens": ["", "omurongo", "omirongo vivari", "omirongo vitatu", "omirongo vine",
             "omirongo vitano", "omirongo hamboumwe", "omirongo hambombari",
             "omirongo hambondatu", "omirongo muvyu"],
    "hundred": "esere", "hundreds": "omasere",
    "thousand": "eyovi", "thousands": "omayovi",
    "and": "na", "zero": "kapena", "point": "komma",
}

# ── Afrikaans ────────────────────────────────────────────────────────────────
AF_UNITS = ["", "een", "twee", "drie", "vier", "vyf", "ses", "sewe", "agt", "nege",
            "tien", "elf", "twaalf", "dertien", "veertien", "vyftien", "sestien",
            "sewentien", "agtien", "negentien"]
AF_TENS = ["", "tien", "twintig", "dertig", "veertig", "vyftig",
           "sestig", "sewentig", "tagtig", "negentig"]

EN_UNITS = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen"]
EN_TENS = ["", "ten", "twenty", "thirty", "forty", "fifty",
           "sixty", "seventy", "eighty", "ninety"]


def _bantu_below_100(n: int, T: Dict) -> str:
    if n < 10:
        return T["units"][n]
    tens, unit = divmod(n, 10)
    out = T["tens"][tens]
    if unit:
        out += f" {T['and']} {T['units'][unit]}"
    return out


def _bantu(n: int, T: Dict) -> str:
    """Bantu numerals: hundreds and thousands are counted, then joined with 'na'."""
    if n == 0:
        return T["zero"]
    parts: List[str] = []
    thousands, rest = divmod(n, 1000)
    if thousands:
        if thousands == 1:
            parts.append(T["thousand"])
        else:
            parts.append(f"{T['thousands']} {_bantu_below_100(thousands, T)}")
    hundreds, rest = divmod(rest, 100)
    if hundreds:
        if hundreds == 1:
            parts.append(T["hundred"])
        else:
            parts.append(f"{T['hundreds']} {_bantu_below_100(hundreds, T)}")
    if rest:
        parts.append(_bantu_below_100(rest, T))
    return f" {T['and']} ".join(parts)


def _afrikaans(n: int) -> str:
    if n == 0:
        return "nul"
    if n < 20:
        return AF_UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return f"{AF_UNITS[unit]}-en-{AF_TENS[tens]}" if unit else AF_TENS[tens]
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        out = f"{AF_UNITS[hundreds]}honderd"
        return f"{out} {_afrikaans(rest)}" if rest else out
    thousands, rest = divmod(n, 1000)
    out = ("een" if thousands == 1 else _afrikaans(thousands)) + "duisend"
    return f"{out} {_afrikaans(rest)}" if rest else out


def _english(n: int) -> str:
    if n == 0:
        return "zero"
    if n < 20:
        return EN_UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return f"{EN_TENS[tens]}-{EN_UNITS[unit]}" if unit else EN_TENS[tens]
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        out = f"{EN_UNITS[hundreds]} hundred"
        return f"{out} and {_english(rest)}" if rest else out
    thousands, rest = divmod(n, 1000)
    out = f"{_english(thousands)} thousand"
    return f"{out} {_english(rest)}" if rest else out


def number_to_words(n: int, lang: str) -> str:
    n = int(n)
    if n < 0:
        return "-" + number_to_words(-n, lang)
    if n > 999999:                      # beyond anything a herd or a price needs
        return str(n)
    table = {"ng": NG, "kj": KJ, "hz": HZ}.get(lang)
    if table:
        return _bantu(n, table)
    if lang == "af":
        return _afrikaans(n)
    return _english(n)


def decimal_to_words(whole: int, frac: str, lang: str) -> str:
    """3.4 -> 'three comma four'. Namibians say komma across all four local languages."""
    joiner = {"af": "komma", "ng": NG["point"], "kj": KJ["point"],
              "hz": HZ["point"]}.get(lang, "point")
    frac_words = " ".join(number_to_words(int(d), lang) for d in frac if d.isdigit())
    return f"{number_to_words(whole, lang)} {joiner} {frac_words}"
