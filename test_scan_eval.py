#!/usr/bin/env python3
"""Scores the notebook scan against pages laid out in different ways.

The point is not "does it read Teo's notebook" — it is "does it read a stock book it
has never seen, kept in a style nobody anticipated". Synthetic fixtures cover the
format archetypes; real photographed pages (worth far more) are picked up
automatically from tests/fixtures/notebook/ once their ground truth is added to
REAL_PAGES below.

    python test_scan_eval.py              # all fixtures
    python test_scan_eval.py A_ E_        # only fixtures whose name starts with these

Costs a couple of API calls per fixture. Needs the app importable (uses main directly,
no server required).
"""
import asyncio
import json
import os
import sys

FIXDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures", "notebook")

# Ground truth for real photographed pages. Add an entry here when you drop a photo in.
REAL_PAGES: dict = {}


def load_truth() -> dict:
    truth = {}
    gt = os.path.join(FIXDIR, "ground_truth.json")
    if os.path.exists(gt):
        with open(gt) as f:
            truth.update(json.load(f))
    truth.update(REAL_PAGES)
    return truth


def norm_tag(t: str) -> str:
    """Tags are read off handwriting; spacing and case are not signal."""
    return "".join(str(t or "").split()).upper()


async def scan(path: str) -> dict:
    import main
    from fastapi import UploadFile
    from starlette.datastructures import Headers

    with open(path, "rb") as f:
        data = f.read()
    ct = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    upload = UploadFile(filename=os.path.basename(path), file=__import__("io").BytesIO(data),
                        headers=Headers({"content-type": ct}))
    return await main.scan_notebook(upload)


def score(name: str, truth: dict, got: dict) -> tuple:
    """Returns (checks_passed, checks_total, failure_lines)."""
    fails, passed, total = [], 0, 0

    def check(ok, label):
        nonlocal passed, total
        total += 1
        if ok:
            passed += 1
        else:
            fails.append(label)

    animals = got.get("animals", [])
    events = got.get("events", [])
    exp_animals = truth.get("animals", [])
    by_tag = {norm_tag(a["tag"]): a for a in animals if a.get("tag")}

    # Hard ceiling: a tally page must not become hundreds of animals.
    if "max_animals" in truth:
        check(len(animals) <= truth["max_animals"],
              f"expected at most {truth['max_animals']} animals, got {len(animals)}")
    if "min_events" in truth:
        check(len(events) >= truth["min_events"],
              f"expected at least {truth['min_events']} events, got {len(events)}")

    # Struck-through rows and marginalia must never become records.
    for bad in truth.get("must_not_contain_tags", []):
        check(norm_tag(bad) not in by_tag, f"struck/marginal '{bad}' was imported")

    if exp_animals:
        tagged = [a for a in exp_animals if a.get("tag")]
        untagged = [a for a in exp_animals if not a.get("tag")]
        check(len(animals) == len(exp_animals),
              f"row count: expected {len(exp_animals)}, got {len(animals)}")
        check(len([a for a in animals if not a.get("tag")]) >= len(untagged),
              f"untagged rows dropped: expected {len(untagged)}")
        for e in tagged:
            g = by_tag.get(norm_tag(e["tag"]))
            if not g:
                check(False, f"missing tag {e['tag']}")
                continue
            check(True, "")
            for field in ("species", "sex", "castrated", "breed", "dob"):
                if field not in e:
                    continue
                gv, ev = g.get(field), e[field]
                if field == "breed":
                    ok = str(ev).lower() in str(gv or "").lower()
                else:
                    ok = gv == ev
                check(ok, f"{e['tag']} {field}: expected {ev!r}, got {gv!r}")
    elif "max_animals" not in truth:
        check(not animals, f"expected no individual animals, got {len(animals)}")

    return passed, total, fails


async def main_async(filters: list) -> int:
    truth_all = load_truth()
    names = sorted(n for n in truth_all
                   if os.path.exists(os.path.join(FIXDIR, n))
                   and (not filters or any(n.startswith(f) for f in filters)))
    if not names:
        print(f"No fixtures found in {FIXDIR}. Run: python tests/make_fixtures.py")
        return 1

    total_p = total_t = 0
    results = []
    for name in names:
        path = os.path.join(FIXDIR, name)
        try:
            got = await scan(path)
        except Exception as e:
            print(f"✗ {name}: scan failed — {e}")
            results.append((name, 0, 1, [f"scan raised: {e}"]))
            total_t += 1
            continue
        p, t, fails = score(name, truth_all[name], got)
        total_p += p
        total_t += t
        mark = "✓" if not fails else "✗"
        print(f"{mark} {name:<32} {p}/{t}"
              f"   animals={len(got.get('animals', []))} events={len(got.get('events', []))}")
        for f in fails:
            print(f"      · {f}")
        for w in got.get("warnings", [])[:4]:
            print(f"      ⚠ {w}")
        results.append((name, p, t, fails))

    pct = 100 * total_p / total_t if total_t else 0
    print(f"\n{total_p}/{total_t} checks passed ({pct:.0f}%) across {len(names)} pages")
    if not REAL_PAGES:
        print("No real photographed pages yet — synthetics alone do not prove this works "
              "on real handwriting. Add photos to tests/fixtures/notebook/ and their "
              "ground truth to REAL_PAGES.")
    return 0 if all(not f for _, _, _, f in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async(sys.argv[1:])))
