"""Aggregate the REAL Lacuna Fund / UNAM / Farm4Trade field forms into data/real_sites.csv.

Sources (archive/), 21 monitoring sites, seasons feb_23 / may_23 / feb_24 / april_24:

- fieldform_cover/*   point-intercept hits per functional group -> cover percentages
    grass_cover_pct        presence rate of perennial + annual grass  (forage base)
    perennial_grass_pct    presence rate of perennial grass           (range health)
    woody_cover_pct        presence rate of tree + shrub              (bush encroachment)
    bare_ground_pct        presence rate of bare ground               (degradation)
    palatable_pct          share of scored hits flagged grazable (G)  (forage quality)
- fieldform_standing/* standing_crop_estimate per quadrat -> standing crop kg/ha (may_23 only)
- fieldform_grazing/*  observed livestock + rainfall records per site (season-independent)

Filename convention: <site>_<form>_<season>.xlsx  e.g. agag_cover_feb_23.xlsx
"""
import glob
import os
import re
import pandas as pd

OUT = "data/real_sites.csv"
GRAZING_OUT = "data/real_grazing.csv"

GRASS = ("perennial_grass", "annual_grass")
WOODY = ("tree", "shrub", "short_shrub")


def site_season(path: str, form: str):
    name = os.path.basename(path).replace(".xlsx", "")
    m = re.match(rf"(.+)_{form}_(.+)", name)
    return (m.group(1), m.group(2)) if m else (None, None)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Field forms were filled by different people; header spelling varies."""
    df.columns = [str(c).strip() for c in df.columns]
    aliases = {"Functional groups": "functional_group", "functional groups": "functional_group",
               "Functional_group": "functional_group", "longitude": "long", "latitude": "lat"}
    return df.rename(columns=aliases)


def _rate(df, groups) -> float | None:
    sub = df[df["functional_group"].isin(groups)]
    p = pd.to_numeric(sub["presence"], errors="coerce")
    return round(100 * p.mean(), 1) if p.notna().any() else None


def build_sites() -> pd.DataFrame:
    rows: dict = {}

    for fp in glob.glob("archive/fieldform_cover/fieldform_cover/*.xlsx"):
        site, season = site_season(fp, "cover")
        if not site:
            continue
        df = normalize(pd.read_excel(fp))
        g = pd.to_numeric(df.get("G"), errors="coerce")
        ng = pd.to_numeric(df.get("NG"), errors="coerce")
        scored = (g.notna() & ng.notna())
        lat = pd.to_numeric(df.get("lat"), errors="coerce").dropna()
        lon = pd.to_numeric(df.get("long"), errors="coerce").dropna()
        rows[(site, season)] = {
            "grass_cover_pct": _rate(df, GRASS),
            "perennial_grass_pct": _rate(df, ("perennial_grass",)),
            "woody_cover_pct": _rate(df, WOODY),
            "bare_ground_pct": _rate(df, ("bare_ground",)),
            "palatable_pct": round(100 * g[scored].mean(), 1) if scored.any() else None,
            "sampling_points": int(df["sampling_point"].nunique()) if "sampling_point" in df else None,
            "lat": round(float(lat.iloc[0]), 5) if len(lat) else None,
            "lon": round(float(lon.iloc[0]), 5) if len(lon) else None,
        }

    for fp in glob.glob("archive/fieldform_standing/fieldform_standing/*.xlsx"):
        site, season = site_season(fp, "standing")
        if not site:
            continue
        df = normalize(pd.read_excel(fp))
        crop = pd.to_numeric(df.get("standing_crop_estimate"), errors="coerce")
        height = pd.to_numeric(df.get("max_height"), errors="coerce")
        rows.setdefault((site, season), {})
        rows[(site, season)].update({
            "standing_crop_kg_ha": round(float(crop.mean()), 1) if crop.notna().any() else None,
            "grass_max_height_cm": round(float(height.mean()), 1) if height.notna().any() else None,
        })

    out = [{"site": s, "season": se, **v} for (s, se), v in sorted(rows.items())]
    return pd.DataFrame(out)


def build_grazing() -> pd.DataFrame:
    recs = []
    for fp in glob.glob("archive/fieldform_grazing/fieldform_grazing/*.xlsx"):
        site = os.path.basename(fp).replace("_grazing.xlsx", "")
        df = normalize(pd.read_excel(fp))
        num = lambda c: pd.to_numeric(df.get(c), errors="coerce")
        rain = num("rainfall")
        rec = {
            "site": site,
            "area_ha": round(float(num("area").dropna().iloc[0]), 0) if num("area").notna().any() else None,
            "cattle_observed": int(num("number_cattle").fillna(0).max()),
            "goats_observed": int(num("number_goat").fillna(0).max()),
            "sheep_observed": int(num("number_sheep").fillna(0).max()),
            "rotational_grazing": int(num("rotational_grazing").fillna(0).max()) if "rotational_grazing" in df else None,
            "rainfall_mm_recorded": round(float(rain.mean()), 1) if rain.notna().any() else None,
            "game_species_seen": int(sum(num(c).fillna(0).max() > 0 for c in
                                         ("number_oryx", "number_kudu", "number_springbok",
                                          "number_hartebeest", "number_zebra", "number_warthog"))),
        }
        recs.append(rec)
    return pd.DataFrame(sorted(recs, key=lambda r: r["site"]))


if __name__ == "__main__":
    sites = build_sites()
    sites.to_csv(OUT, index=False)
    grazing = build_grazing()
    grazing.to_csv(GRAZING_OUT, index=False)
    print(f"Wrote {OUT}: {len(sites)} site-season records across {sites['site'].nunique()} sites")
    print(sites.head(8).to_string())
    print(f"\nWrote {GRAZING_OUT}: {len(grazing)} sites")
    print(grazing.head(5).to_string())
