"""Namibian livestock vocabulary, in one place.

Farmers write their stock books in whatever mixture of English, Afrikaans, Oshiwambo
and Otjiherero they think in, and they do not use the words a schema designer would
pick. A page will say "Kapater" where the database wants sex=male, castrated=true, and
it will happily call a female goat an "Ewe" because that is the word in the head of
the person holding the pen.

This table is the shared answer to "what did they mean". The notebook-scan prompts
render it in, and it is the place to add a term the moment a real page teaches us one
— not the prompt string, which is written text and drifts.

Deliberately NOT a description of any one notebook's layout. Layout is detected per
page (see main.py SCAN_PASS1_PROMPT); only vocabulary lives here.
"""
from typing import Dict, List

# Sex and reproductive status. Note that these overlap across species on purpose:
# farmers routinely use sheep words for goats and vice versa, and correcting them
# loses information we were given.
SEX_TERMS: Dict[str, Dict[str, List[str]]] = {
    "female": {
        "en": ["ewe", "cow", "doe", "heifer", "female", "f", "she"],
        "af": ["ooi", "koei", "vers", "verse", "sy", "wyfie"],
        "ng": ["onzi", "ongombe onkadhi", "oshikombo shonkadhi", "onkadhi"],
        "hz": ["onḓu", "ongombe onḓema", "ongombo onḓema", "onḓema"],
    },
    "male_intact": {
        "en": ["ram", "bull", "buck", "billy", "male", "m", "he", "sire"],
        "af": ["ram", "bul", "bok", "reun", "reün", "mannetjie"],
        "ng": ["ondume", "ongombe ondume", "oshikombo shondume"],
        "hz": ["ondwezu", "ongombe ondwezu", "ongombo ondwezu"],
    },
    # The category the old schema had no room for at all. Very common in small stock:
    # castrated males are kept for meat and are neither "male breeding" nor "female".
    "male_castrated": {
        "en": ["wether", "ox", "steer", "bullock", "castrate", "castrated", "gelding"],
        "af": ["kapater", "hamel", "os", "tollie", "gesnyde", "kapaterbok"],
        "ng": ["ongombe ya tetwa", "oshikombo sha tetwa"],
        "hz": ["ongombe ndja horekwa"],
    },
}

AGE_TERMS: Dict[str, List[str]] = {
    "young": ["lamb", "lam", "calf", "kalf", "kid", "speenkalf", "weaner", "speenlam",
              "okanona", "okambushe", "kid goat", "juvenile"],
    "adult": ["adult", "volwasse", "grown", "mature"],
}

SPECIES_TERMS: Dict[str, List[str]] = {
    "cattle": ["cattle", "cow", "cows", "beeste", "bees", "bul", "oongombe", "ongombe",
               "eengobe", "ozongombe", "beef", "nguni", "brahman", "afrikaner", "sanga"],
    "goat": ["goat", "goats", "bokke", "bok", "iikombo", "oshikombo", "eekombwe",
             "ozongombo", "boer goat", "boerbok", "kalahari red", "savanna"],
    "sheep": ["sheep", "sheeps", "skape", "skaap", "oonzi", "onzi", "eedi", "ozonḓu",
              "dorper", "damara", "karakul", "persian", "swakara", "van rooy"],
}

# Written on pages but never a field value: contact details, running totals, page
# furniture. Extracted text that looks like these is furniture, not data.
NON_DATA_PATTERNS = [
    "phone numbers (081/085/060/061… Namibian mobile and landline formats)",
    "page totals, subtotals, running counts written in a margin",
    "dates written in a margin as when the page was compiled",
    "names and addresses of the owner or the buyer",
    "text bleeding through from the facing page",
]


def _flat(terms: Dict[str, List[str]]) -> str:
    return ", ".join(sorted({w for words in terms.values() for w in words}))


def sex_vocabulary_block() -> str:
    """Rendered into the structuring prompt so the mapping rules stay in one place."""
    return (
        f"FEMALE — {_flat(SEX_TERMS['female'])}\n"
        f"MALE, intact — {_flat(SEX_TERMS['male_intact'])}\n"
        f"MALE, castrated (sex=male AND castrated=true) — {_flat(SEX_TERMS['male_castrated'])}\n"
        f"Young animal (a note, not a sex) — {', '.join(AGE_TERMS['young'])}"
    )


def species_vocabulary_block() -> str:
    return "\n".join(f"{k.upper()} — {', '.join(v)}" for k, v in SPECIES_TERMS.items())


def non_data_block() -> str:
    return "\n".join(f"- {p}" for p in NON_DATA_PATTERNS)
