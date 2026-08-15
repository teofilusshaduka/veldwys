#!/usr/bin/env python3
"""Render synthetic notebook pages for the scan eval.

These exist to prove the pipeline is not tuned to one farmer's layout. Each fixture is
a deliberately different way of keeping stock records — columns in another order, no
header row, no table at all, an event diary, a tally, a printed card. Real photographed
pages are worth more than all of these; drop them in tests/fixtures/notebook/ and add
their ground truth to REAL_PAGES in test_scan_eval.py.

    python tests/make_fixtures.py

Needs Google Chrome (headless screenshot). Writes PNG + ground_truth.json.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "notebook")
SRC = os.path.join(OUT, "src")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PAGE_CSS = """
body { margin:0; padding:46px 54px; background:#fdfcf7; width:1100px;
       font-family:'Bradley Hand','Noteworthy','Marker Felt',cursive; color:#1a2540; }
h1 { font-size:34px; font-weight:normal; text-align:center; margin:0 0 26px; }
h2 { font-size:29px; font-weight:normal; margin:26px 0 10px; text-decoration:underline; }
table { width:100%; border-collapse:collapse; font-size:25px; }
td, th { border:1px solid #7c86a0; padding:9px 13px; text-align:left; font-weight:normal; }
th { font-size:23px; }
.strike { text-decoration:line-through; color:#5a6482; }
ol { font-size:26px; line-height:1.85; }
.margin { font-size:21px; color:#6b7characters; }
.note { font-size:21px; color:#6b7490; margin-top:20px; }
.card-row { font-size:26px; margin:14px 0; border-bottom:1px solid #9aa3bb; padding-bottom:6px; }
.label { font-family:Helvetica,Arial,sans-serif; font-size:19px; color:#333; }
"""

FIXTURES = {}

# ── A. No header row, columns in a different order (sex, markings, tag) ──────
FIXTURES["A_headerless_reordered"] = {
    "html": """
<h2>Skape</h2>
<table>
<tr><td>Ooi</td><td>white, brown face</td><td>NK 104</td></tr>
<tr><td>Ram</td><td>all brown</td><td>NK 105</td></tr>
<tr><td>Kapater</td><td>white, black legs</td><td>NK 106</td></tr>
<tr><td>Ooi</td><td>black and white</td><td>NK 107</td></tr>
<tr class="strike"><td>Ooi</td><td>brown spotted</td><td>NK 108</td></tr>
<tr><td>Ooi</td><td>white</td><td>NK 109</td></tr>
<tr><td>Kapater</td><td>dark brown, white tail</td><td>NK 110</td></tr>
</table>
<div class="note">081 447 2210</div>
""",
    "truth": {
        "record_type": "individual_animals",
        "animals": [
            {"tag": "NK 104", "species": "sheep", "sex": "female", "castrated": False},
            {"tag": "NK 105", "species": "sheep", "sex": "male", "castrated": False},
            {"tag": "NK 106", "species": "sheep", "sex": "male", "castrated": True},
            {"tag": "NK 107", "species": "sheep", "sex": "female", "castrated": False},
            {"tag": "NK 109", "species": "sheep", "sex": "female", "castrated": False},
            {"tag": "NK 110", "species": "sheep", "sex": "male", "castrated": True},
        ],
        "must_not_contain_tags": ["NK 108", "081 447 2210"],
    },
}

# ── B. Not a table at all — one animal per written line ──────────────────────
FIXTURES["B_freetext_list"] = {
    "html": """
<h1>My goats</h1>
<ol>
<li>G12 brown, white on stomach, ewe</li>
<li>G13 white, doe</li>
<li>G14 black and white buck</li>
<li>G15 brown ewe, small</li>
<li>white with brown face, doe, no tag yet</li>
<li>G17 kapater, all white</li>
</ol>
""",
    "truth": {
        "record_type": "individual_animals",
        "animals": [
            {"tag": "G12", "species": "goat", "sex": "female", "castrated": False},
            {"tag": "G13", "species": "goat", "sex": "female", "castrated": False},
            {"tag": "G14", "species": "goat", "sex": "male", "castrated": False},
            {"tag": "G15", "species": "goat", "sex": "female", "castrated": False},
            {"tag": "", "species": "goat", "sex": "female", "castrated": False},
            {"tag": "G17", "species": "goat", "sex": "male", "castrated": True},
        ],
    },
}

# ── C. Event diary. Must NOT invent one animal per line ──────────────────────
FIXTURES["C_event_log"] = {
    "html": """
<h1>Farm diary 2026</h1>
<table>
<tr><th>Date</th><th>What was done</th></tr>
<tr><td>2026-03-12</td><td>Vaccinated all cattle for anthrax</td></tr>
<tr><td>2026-03-14</td><td>Treated B22 for lumpy skin</td></tr>
<tr><td>2026-04-02</td><td>Moved sheep to the east camp</td></tr>
<tr><td>2026-04-19</td><td>Dosed all goats for worms</td></tr>
<tr><td>2026-05-08</td><td>B22 sold at Otjiwarongo</td></tr>
</table>
""",
    "truth": {
        "record_type": "event_log",
        "animals": [],
        "min_events": 4,
        "note": "the page names no individual animals to register; B22 is referenced, not listed",
    },
}

# ── D. Tally sheet. Must NOT emit 47 cattle records ──────────────────────────
FIXTURES["D_tally_counts"] = {
    "html": """
<h1>Count 30 June</h1>
<table>
<tr><td>Cattle</td><td>47</td></tr>
<tr><td>Goats</td><td>112</td></tr>
<tr><td>Sheep</td><td>63</td></tr>
<tr><td>Donkeys</td><td>4</td></tr>
</table>
<div class="note">Total 226</div>
""",
    "truth": {
        "record_type": "tally_counts",
        "animals": [],
        "max_animals": 0,
        "min_events": 3,
        "note": "counts only — inventing 226 animal records here would be the failure",
    },
}

# ── E. Afrikaans column headers ──────────────────────────────────────────────
FIXTURES["E_afrikaans_headers"] = {
    "html": """
<h1>Beeste</h1>
<table>
<tr><th>Oormerk</th><th>Beskrywing</th><th>Geslag</th><th>Ras</th></tr>
<tr><td>OV 21</td><td>rooi, wit kop</td><td>Koei</td><td>Brahman</td></tr>
<tr><td>OV 22</td><td>swart</td><td>Bul</td><td>Nguni</td></tr>
<tr><td>OV 23</td><td>bruin, wit pens</td><td>Os</td><td>Brahman</td></tr>
<tr><td>OV 24</td><td>rooi bont</td><td>Vers</td><td>Nguni</td></tr>
<tr><td>OV 25</td><td>swart wit</td><td>Koei</td><td></td></tr>
</table>
""",
    "truth": {
        "record_type": "individual_animals",
        "animals": [
            {"tag": "OV 21", "species": "cattle", "sex": "female", "castrated": False, "breed": "Brahman"},
            {"tag": "OV 22", "species": "cattle", "sex": "male", "castrated": False, "breed": "Nguni"},
            {"tag": "OV 23", "species": "cattle", "sex": "male", "castrated": True, "breed": "Brahman"},
            {"tag": "OV 24", "species": "cattle", "sex": "female", "castrated": False, "breed": "Nguni"},
            {"tag": "OV 25", "species": "cattle", "sex": "female", "castrated": False},
        ],
    },
}

# ── F. Printed form filled in by hand ────────────────────────────────────────
FIXTURES["F_printed_card"] = {
    "html": """
<h1>STOCK CARD</h1>
<div class="card-row"><span class="label">Ear tag no.:</span> &nbsp; DR 0091</div>
<div class="card-row"><span class="label">Species:</span> &nbsp; Sheep</div>
<div class="card-row"><span class="label">Breed:</span> &nbsp; Dorper</div>
<div class="card-row"><span class="label">Sex:</span> &nbsp; Ewe</div>
<div class="card-row"><span class="label">Colour / markings:</span> &nbsp; white, black head</div>
<div class="card-row"><span class="label">Date of birth:</span> &nbsp; 2024-08-15</div>
<div class="card-row"><span class="label">Vaccinations:</span> &nbsp; Pulpy kidney 2025-11-03</div>
""",
    "truth": {
        "record_type": "individual_animals",
        "animals": [
            {"tag": "DR 0091", "species": "sheep", "sex": "female", "castrated": False,
             "breed": "Dorper", "dob": "2024-08-15"},
        ],
        "min_events": 1,
    },
}


def render(name: str, body: str) -> str:
    html_path = os.path.join(SRC, f"{name}.html")
    png_path = os.path.join(OUT, f"{name}.png")
    with open(html_path, "w") as f:
        f.write(f"<!doctype html><meta charset='utf-8'><style>{PAGE_CSS}</style>{body}")
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
         f"--screenshot={png_path}", "--window-size=1200,1500", f"file://{html_path}"],
        check=True, capture_output=True,
    )
    return png_path


def main() -> int:
    if not os.path.exists(CHROME):
        print(f"Google Chrome not found at {CHROME} — cannot render fixtures.")
        return 1
    os.makedirs(SRC, exist_ok=True)
    truth = {}
    for name, spec in FIXTURES.items():
        path = render(name, spec["html"])
        truth[f"{name}.png"] = spec["truth"]
        print(f"  {os.path.basename(path):<34} {os.path.getsize(path):>8,} bytes")
    with open(os.path.join(OUT, "ground_truth.json"), "w") as f:
        json.dump(truth, f, indent=2)
    print(f"\n{len(truth)} fixtures + ground_truth.json in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
