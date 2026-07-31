"""Agent tools: rangeland data, weather fusion, grazing math, livestock register.

All tools are async. main.py calls execute_tool(name, args, user_id, profile),
which injects sensible defaults from the farmer's profile before dispatch.
"""
import asyncio
import math
import os
import time
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List

import httpx
import pandas as pd

import db

try:
    df_rangeland = pd.read_csv("data/rangeland.csv")
except FileNotFoundError:
    df_rangeland = pd.DataFrame()

try:
    df_real = pd.read_csv("data/real_sites.csv")
except FileNotFoundError:
    df_real = pd.DataFrame()


# --- Namibia's 14 regions: approximate centroids for lat/lon <-> region mapping ---
REGION_CENTROIDS = {
    "Zambezi": (-17.8, 24.3),
    "Kavango East": (-18.2, 20.8),
    "Kavango West": (-18.0, 19.3),
    "Kunene": (-19.5, 13.8),
    "Omusati": (-18.0, 14.9),
    "Oshana": (-18.0, 15.7),
    "Ohangwena": (-17.6, 16.3),
    "Oshikoto": (-18.4, 16.9),
    "Otjozondjupa": (-20.5, 17.5),
    "Omaheke": (-21.8, 19.7),
    "Erongo": (-21.8, 15.1),
    "Khomas": (-22.6, 17.1),
    "Hardap": (-24.5, 17.5),
    "Karas": (-27.0, 17.8),
}


def region_from_latlon(lat: float, lon: float) -> str:
    best, best_d = "Khomas", float("inf")
    for region, (rlat, rlon) in REGION_CENTROIDS.items():
        d = (lat - rlat) ** 2 + (lon - rlon) ** 2
        if d < best_d:
            best, best_d = region, d
    return best


def latlon_from_region(region: str) -> Optional[tuple]:
    for name, coords in REGION_CENTROIDS.items():
        if name.lower().replace(" ", "") == region.lower().replace(" ", "").replace("//", ""):
            return coords
    return None


# =========================== RANGELAND (synthetic starter) ===========================

async def query_rangeland(region: str, site_id: Optional[str] = None,
                          tenure: Optional[str] = None,
                          compare_tenure: bool = False, **kw) -> Dict[str, Any]:
    if df_rangeland.empty:
        return {"error": "Rangeland dataset not loaded."}

    region_norm = region.strip().lower().replace("//", "")
    df = df_rangeland[df_rangeland["region"].str.lower().str.replace("//", "") == region_norm]
    if tenure:
        df = df[df["tenure"].str.lower() == tenure.lower()]
    if site_id:
        df = df[df["site_id"].str.lower() == site_id.lower()]
    if df.empty:
        return {"error": f"No data found for region '{region}'. Valid regions: {sorted(df_rangeland['region'].unique().tolist())}"}

    agg = {
        "avg_veg_cover_pct": round(df["veg_cover_pct"].mean(), 1),
        "avg_ndvi": round(df["ndvi"].mean(), 3),
        "avg_grass_biomass_kg_ha": round(df["grass_biomass_kg_ha"].mean(), 0),
        "avg_carrying_capacity_ha_per_lsu": round(df["carrying_capacity_ha_lsu"].mean(), 1),
        "common_bush_encroachment": df["bush_encroachment"].mode().iloc[0] if not df["bush_encroachment"].mode().empty else "Unknown",
        "grazing_pressure_distribution": df["grazing_pressure"].value_counts().to_dict(),
        "sites_sampled": len(df),
    }
    result: Dict[str, Any] = {
        "region": region,
        "summary": agg,
        "data_source": "Synthetic starter dataset (1,200 sites, all 14 regions) modeled on Namibia's Rangeland & Pasture Dataset",
    }
    if compare_tenure:
        by_tenure = {}
        for t, g in df_rangeland[df_rangeland["region"].str.lower().str.replace("//", "") == region_norm].groupby("tenure"):
            by_tenure[t] = {
                "avg_veg_cover_pct": round(g["veg_cover_pct"].mean(), 1),
                "avg_grass_biomass_kg_ha": round(g["grass_biomass_kg_ha"].mean(), 0),
                "avg_carrying_capacity_ha_per_lsu": round(g["carrying_capacity_ha_lsu"].mean(), 1),
                "sites": len(g),
            }
        result["tenure_comparison"] = by_tenure
    return result


METRIC_LABELS = {
    "grass_cover_pct": "grass cover %",
    "perennial_grass_pct": "perennial grass %",
    "woody_cover_pct": "bush/tree cover %",
    "bare_ground_pct": "bare ground %",
    "palatable_pct": "palatable (grazable) plants %",
    "standing_crop_kg_ha": "standing crop kg/ha",
}
# Metrics where a rise is bad for the farmer
WORSE_WHEN_UP = {"woody_cover_pct", "bare_ground_pct"}

# Field visits in chronological order (filenames sort alphabetically, which is wrong)
SEASON_ORDER = ["feb_23", "may_23", "feb_24", "april_24"]
SEASON_LABELS = {"feb_23": "February 2023", "may_23": "May 2023",
                 "feb_24": "February 2024", "april_24": "April 2024"}


def _nearest_real_site(lat: float, lon: float) -> Optional[str]:
    if df_real.empty or "lat" not in df_real:
        return None
    d = df_real.dropna(subset=["lat", "lon"])
    if d.empty:
        return None
    dist = (d["lat"] - lat) ** 2 + (d["lon"] - lon) ** 2
    return d.loc[dist.idxmin(), "site"]


async def compare_seasons(site: Optional[str] = None, lat: Optional[float] = None,
                          lon: Optional[float] = None, **kw) -> Dict[str, Any]:
    """Same-season year-over-year comparison from the REAL Lacuna field dataset.

    Feb 2023 vs Feb 2024 is a like-for-like comparison at the same monitoring sites.
    """
    if df_real.empty:
        return {"error": "Real field dataset not available."}

    chosen = None
    if site:
        m = df_real[df_real["site"].str.lower().str.contains(site.lower())]
        if not m.empty:
            chosen = m.iloc[0]["site"]
    if chosen is None and lat is not None and lon is not None:
        chosen = _nearest_real_site(lat, lon)

    def site_block(sname: str) -> Dict[str, Any]:
        g = df_real[df_real["site"] == sname].set_index("season")
        ordered = [s for s in SEASON_ORDER if s in g.index]
        block: Dict[str, Any] = {
            "site": sname,
            "visits": [SEASON_LABELS.get(s, s) for s in ordered],
        }
        changes = []
        if "feb_23" in g.index and "feb_24" in g.index:
            a, b = g.loc["feb_23"], g.loc["feb_24"]
            for metric, label in METRIC_LABELS.items():
                if metric in g.columns and pd.notna(a.get(metric)) and pd.notna(b.get(metric)):
                    before, after = float(a[metric]), float(b[metric])
                    delta = round(after - before, 1)
                    if abs(delta) < 0.5:
                        direction = "about the same"
                    elif (delta > 0) == (metric in WORSE_WHEN_UP):
                        direction = "worse"
                    else:
                        direction = "better"
                    changes.append({"metric": label, "feb_2023": before, "feb_2024": after,
                                    "change": delta, "reading": direction})
            block["same_season_comparison"] = {"window": "February 2023 vs February 2024",
                                               "changes": changes}
        latest = ordered[-1] if ordered else None
        if latest is not None:
            block["latest_visit"] = {"season": SEASON_LABELS.get(latest, latest), **{
                k: (round(float(g.loc[latest, k]), 1) if pd.notna(g.loc[latest, k]) else None)
                for k in METRIC_LABELS if k in g.columns}}
        return block

    sites = [site_block(chosen)] if chosen else [site_block(s) for s in df_real["site"].unique()[:4]]
    return {
        "sites": sites,
        "sites_available": sorted(df_real["site"].unique().tolist()),
        "data_source": ("REAL field measurements from Namibia's Rangeland & Pasture Dataset "
                        "(Lacuna Fund / UNAM / Farm4Trade), 21 monitoring sites visited "
                        "Feb 2023, May 2023, Feb 2024 and April 2024"),
        "method": "Point-intercept cover surveys (50 sampling points per site) plus clipped standing-crop quadrats.",
        "caveat": "These are monitoring sites, not the farmer's own camp, treat as the regional signal, not a measurement of their veld.",
    }


# =========================== WEATHER FUSION ===========================

_weather_cache: Dict[str, Any] = {}
WEATHER_TTL = 6 * 3600


async def _fetch_open_meteo(client: httpx.AsyncClient, lat: float, lon: float) -> Dict[str, Any]:
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           f"&daily=precipitation_sum&past_days=90&forecast_days=7&timezone=Africa%2FWindhoek")
    resp = await client.get(url, timeout=12)
    resp.raise_for_status()
    daily = resp.json().get("daily", {}).get("precipitation_sum", []) or []
    daily = [v if v is not None else 0.0 for v in daily]
    hist, fc = daily[:90], daily[90:]
    return {
        "rain_30_mm": sum(hist[-30:]),
        "rain_60_mm": sum(hist[-60:]),
        "rain_90_mm": sum(hist),
        "forecast_7d_mm": sum(fc[:7]),
    }


async def _fetch_nasa_power(client: httpx.AsyncClient, lat: float, lon: float) -> Dict[str, Any]:
    end = datetime.now()
    start = end - timedelta(days=95)
    url = (f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR"
           f"&community=AG&longitude={lon}&latitude={lat}"
           f"&start={start.strftime('%Y%m%d')}&end={end.strftime('%Y%m%d')}&format=JSON")
    resp = await client.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json().get("properties", {}).get("parameter", {}).get("PRECTOTCORR", {})
    values = [v for v in data.values() if v is not None and v != -999.0]
    return {
        "rain_30_mm": sum(values[-30:]),
        "rain_60_mm": sum(values[-60:]),
        "rain_90_mm": sum(values[-90:]),
    }


async def _fetch_climatology(client: httpx.AsyncClient, lat: float, lon: float) -> Dict[str, float]:
    """NASA POWER long-term monthly precipitation normals (mm/day per month)."""
    url = (f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=PRECTOTCORR"
           f"&community=AG&longitude={lon}&latitude={lat}&format=JSON")
    resp = await client.get(url, timeout=15)
    resp.raise_for_status()
    monthly = resp.json().get("properties", {}).get("parameter", {}).get("PRECTOTCORR", {})
    # keys are JAN.DEC (+ ANN); values mm/day
    order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    return {m: monthly.get(m, 0.0) for m in order}


def _normal_for_window(monthly_mm_day: Dict[str, float], days: int) -> float:
    """Expected rainfall for the trailing `days` window from monthly normals."""
    order = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    total, d = 0.0, date.today()
    for i in range(days):
        day = d - timedelta(days=i)
        total += monthly_mm_day.get(order[day.month - 1], 0.0)
    return total


async def get_rainfall(lat: float, lon: float, **kw) -> Dict[str, Any]:
    key = f"{round(lat, 2)},{round(lon, 2)}"
    cached = _weather_cache.get(key)
    if cached and time.time() - cached["ts"] < WEATHER_TTL:
        return cached["data"]

    async with httpx.AsyncClient() as client:
        om, np_, clim = await asyncio.gather(
            _fetch_open_meteo(client, lat, lon),
            _fetch_nasa_power(client, lat, lon),
            _fetch_climatology(client, lat, lon),
            return_exceptions=True,
        )

    om_ok = isinstance(om, dict)
    np_ok = isinstance(np_, dict)
    if not om_ok and not np_ok:
        return {"error": "Both weather APIs failed. Try again shortly."}

    if om_ok and np_ok:
        diff = abs(om["rain_60_mm"] - np_["rain_60_mm"])
        avg60 = (om["rain_60_mm"] + np_["rain_60_mm"]) / 2
        rel = diff / avg60 if avg60 > 0 else 0
        # In the dry season both sources sit near zero; a relative difference between
        # 1 mm and 6 mm is arithmetic noise, not genuine disagreement.
        agree = rel <= 0.25 or diff <= 8.0
        result = {
            "rain_30_mm": round((om["rain_30_mm"] + np_["rain_30_mm"]) / 2, 1) if agree else None,
            "rain_60_mm": round(avg60, 1) if agree else None,
            "rain_90_mm": round((om["rain_90_mm"] + np_["rain_90_mm"]) / 2, 1) if agree else None,
            "range_60d_mm": None if agree else f"{min(om['rain_60_mm'], np_['rain_60_mm']):.0f} to {max(om['rain_60_mm'], np_['rain_60_mm']):.0f}",
            "confidence": "High (two independent sources agree)" if agree else "Moderate (sources disagree; range reported)",
            "sources_agree_pct": round(max(0.0, 100 - rel * 100), 0),
            "sources_used": ["Open-Meteo", "NASA POWER"],
            "forecast_7d_mm": round(om["forecast_7d_mm"], 1),
        }
    else:
        src = om if om_ok else np_
        result = {
            "rain_30_mm": round(src["rain_30_mm"], 1),
            "rain_60_mm": round(src["rain_60_mm"], 1),
            "rain_90_mm": round(src["rain_90_mm"], 1),
            "confidence": "Single-source (one weather API unavailable)",
            "sources_used": ["Open-Meteo"] if om_ok else ["NASA POWER"],
            "forecast_7d_mm": round(src.get("forecast_7d_mm", 0), 1) if om_ok else None,
        }

    if isinstance(clim, dict):
        normal_60 = _normal_for_window(clim, 60)
        actual_60 = result.get("rain_60_mm")
        if actual_60 is None and om_ok and np_ok:
            actual_60 = (om["rain_60_mm"] + np_["rain_60_mm"]) / 2
        if actual_60 is not None:
            result["normal_60d_mm"] = round(normal_60, 1)
            result["climatology_source"] = "NASA POWER multi-year normals"
            # Percentage anomalies are only meaningful once the baseline is non-trivial.
            # Namibia's dry season normal is near zero, where "+97% above normal" would
            # describe a 3 mm shower.
            if normal_60 >= 15:
                result["anomaly_vs_normal_pct"] = round((actual_60 / normal_60 - 1) * 100, 0)
            else:
                result["anomaly_vs_normal_pct"] = None
                result["season_note"] = (
                    f"This is the dry season here, only about {normal_60:.0f} mm is normal for "
                    "this 60-day window, so percentage comparisons are not meaningful. "
                    "Judge the veld on standing grass, not recent rain.")

    _weather_cache[key] = {"ts": time.time(), "data": result}
    return result


# =========================== GRAZING MATH ===========================

async def estimate_grazing_days(grass_biomass_kg_ha: float, area_ha: float,
                                herd_lsu: float, **kw) -> Dict[str, Any]:
    utilization_factor = 0.30       # keep 70% standing for range health
    daily_intake_kg = 12.0          # dry matter per LSU per day
    usable = grass_biomass_kg_ha * area_ha * utilization_factor
    intake = herd_lsu * daily_intake_kg
    days = usable / intake if intake > 0 else float("inf")
    density = area_ha / herd_lsu if herd_lsu > 0 else float("inf")

    out: Dict[str, Any] = {
        "usable_forage_kg": round(usable, 0),
        "current_density_ha_per_lsu": round(density, 1) if math.isfinite(density) else None,
        "assumptions": "30% utilization factor, 12 kg dry matter/LSU/day",
    }
    # A forage-only figure becomes meaningless past a season, grass quality, water and
    # regrowth bind long before the biomass runs out. Report it as a ceiling instead.
    if not math.isfinite(days):
        out["days_remaining"] = None
        out["interpretation"] = "No livestock recorded, so there is nothing grazing this camp."
    elif days > 270:
        out["days_remaining"] = "more than a full season"
        out["interpretation"] = (
            f"Forage is not the limiting factor here, at {round(density)} ha per LSU this camp is "
            "stocked very lightly. Water, grass quality and rotation matter more than quantity. "
            "Do NOT quote a day count; say the camp comfortably carries this herd for the season.")
    else:
        out["days_remaining"] = round(days, 0)
        out["interpretation"] = "Forage-based estimate only; check water and veld condition on the ground."
    return out


# =========================== LIVESTOCK REGISTER ===========================

async def get_herd_summary(user_id: int = 0, **kw) -> Dict[str, Any]:
    return db.get_herd_summary(user_id)


async def search_animals(user_id: int = 0, query: Optional[str] = None,
                         species: Optional[str] = None, status: Optional[str] = None,
                         **kw) -> Dict[str, Any]:
    animals = db.get_animals(user_id, status=status, species=species, query=query)
    return {
        "matches": len(animals),
        "animals": [
            {"id": a["id"], "tag": a["tag"], "name": a["name"], "species": a["species"],
             "breed": a["breed"], "sex": a["sex"], "dob": a["dob"], "status": a["status"],
             "notes": (a["notes"][:80] if a["notes"] else "")}
            for a in animals[:15]
        ],
    }


async def get_upcoming_tasks(user_id: int = 0, days: int = 30, **kw) -> Dict[str, Any]:
    events = db.get_upcoming_events(user_id, days=days)
    return {
        "window_days": days,
        "count": len(events),
        "tasks": [
            {"id": e["id"], "type": e["event_type"], "due": e["due_date"],
             "overdue": e["overdue"], "description": e["description"],
             "animal": (e.get("animal_tag") or e.get("animal_name") or "whole herd")}
            for e in events[:20]
        ],
    }


async def log_livestock_event(user_id: int = 0, event_type: str = "note",
                              description: str = "", animal_tag: Optional[str] = None,
                              event_date: str = "", due_date: Optional[str] = None,
                              **kw) -> Dict[str, Any]:
    animal_id = None
    if animal_tag:
        matches = db.get_animals(user_id, query=animal_tag)
        if matches:
            animal_id = matches[0]["id"]
    eid = db.add_animal_event(user_id, event_type=event_type, description=description,
                              animal_id=animal_id, event_date=event_date, due_date=due_date)
    return {"saved": True, "event_id": eid,
            "linked_animal": animal_tag if animal_id else None,
            "note": "Recorded in the farm register." + ("" if animal_id or not animal_tag else f" No animal matched tag '{animal_tag}'; saved as herd-wide event.")}


async def update_animals(user_id: int = 0, action: str = "sold",
                         tags: Optional[List[str]] = None, species: Optional[str] = None,
                         count: int = 1, **kw) -> Dict[str, Any]:
    """Change animal status in bulk. Always reports exactly which animals moved."""
    action = (action or "sold").lower()
    if action not in ("sold", "deceased", "active"):
        return {"error": "action must be sold, deceased or active"}
    picked = db.pick_animals(user_id, species=species, count=count, tags=tags)
    if not picked:
        return {"error": f"No matching animals found"
                         + (f" with tag(s) {tags}" if tags else f" of species {species}"),
                "changed": 0}
    db.set_animal_status(user_id, [a["id"] for a in picked], action)
    herd = db.get_herd_summary(user_id)
    return {
        "changed": len(picked),
        "status": action,
        "animals": [{"tag": a["tag"] or f"#{a['id']}", "species": a["species"],
                     "name": a["name"]} for a in picked],
        "herd_now": herd["counts"],
        "note": ("These animals were chosen automatically because no ear tags were given. "
                 "Tell the farmer which ones and let them correct you.") if not tags else None,
    }


async def complete_task(user_id: int = 0, query: str = "", **kw) -> Dict[str, Any]:
    """Mark a due vaccination or treatment as done, matched loosely by description."""
    matches = db.find_open_events(user_id, query=query)
    if not matches:
        return {"error": f"No open task matching '{query}'.",
                "open_tasks": [e["description"][:70] for e in db.find_open_events(user_id)]}
    if len(matches) > 1 and query:
        exact = [m for m in matches if query.lower() in (m["description"] or "").lower()]
        matches = exact or matches
    done = matches[0]
    db.complete_event(user_id, done["id"])
    return {"completed": True, "task": done["description"][:100],
            "was_due": done["due_date"],
            "still_open": len(db.find_open_events(user_id))}


# Indicative Namibian auction ranges. Deliberately static and clearly labelled: the
# agent used to invent prices, which is the worst possible failure for a sale decision.
MARKET_PRICES = {
    "cattle": {"weaner": (7000, 11000), "ox": (12000, 18000), "cow": (9000, 15000),
               "bull": (18000, 35000)},
    "goat": {"kid": (700, 1200), "ewe": (1200, 2000), "ram": (1800, 3200)},
    "sheep": {"lamb": (900, 1500), "ewe": (1400, 2200), "ram": (2000, 3500)},
}


async def get_market_prices(species: Optional[str] = None, **kw) -> Dict[str, Any]:
    data = {species.lower(): MARKET_PRICES[species.lower()]} if species and species.lower() in MARKET_PRICES else MARKET_PRICES
    return {
        "currency": "N$ (Namibian dollars)",
        "prices": {sp: {cls: f"N${lo:,} to N${hi:,}" for cls, (lo, hi) in classes.items()}
                   for sp, classes in data.items()},
        "basis": "Indicative live-auction ranges for Namibia, typical recent seasons.",
        "must_say": ("These are indicative ranges only, not today's prices. Tell the farmer to "
                     "confirm with their local auction house (Agra, Gobabis, Windhoek) before "
                     "deciding. Never present these as current or guaranteed."),
    }


async def register_animal(user_id: int = 0, species: str = "cattle", tag: str = "",
                          name: str = "", breed: str = "", sex: str = "",
                          dob: str = "", notes: str = "", **kw) -> Dict[str, Any]:
    aid = db.add_animal(user_id, tag=tag, name=name, species=species, breed=breed,
                        sex=sex, dob=dob, notes=notes)
    return {"saved": True, "animal_id": aid, "species": species, "tag": tag or "(none)"}


async def read_documents(user_id: int = 0, query: Optional[str] = None, **kw) -> Dict[str, Any]:
    """Read documents the farmer uploaded (product labels, letters, lease agreements)."""
    docs = db.get_documents(user_id, query=query)
    if not docs:
        return {"found": 0, "note": "The farmer has not uploaded any matching documents."}
    return {
        "found": len(docs),
        "documents": [{"filename": d["filename"], "excerpt": (d["content"] or "")[:1200]}
                      for d in docs[:3]],
    }


async def get_farm_analytics(user_id: int = 0, **kw) -> Dict[str, Any]:
    import analytics
    return await analytics.summary_for_agent(user_id)


# =========================== TOOL SCHEMAS + DISPATCH ===========================

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "query_rangeland",
        "description": "Rangeland/pasture condition for a Namibian region: vegetation cover, NDVI, grass biomass, carrying capacity, bush encroachment, grazing pressure. Set compare_tenure=true to compare communal vs commercial vs conservancy land.",
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "description": "Namibian region, e.g. Omaheke. Defaults to the farmer's region."},
                "tenure": {"type": "string", "description": "Optional filter: communal | commercial | conservancy"},
                "compare_tenure": {"type": "boolean", "description": "Compare land tenure types in this region"},
            },
            "required": [],
        },
    },
    {
        "name": "compare_seasons",
        "description": "REAL ground-measured field data from Namibia's Rangeland & Pasture Dataset: same-season year-over-year change (Feb 2023 vs Feb 2024) in grass cover, perennial grass, bush encroachment, bare ground and standing crop at 21 monitoring sites. Use for 'how does my pasture compare to the same time last year' and bush-encroachment-trend questions. Defaults to the site nearest the farmer.",
        "parameters": {
            "type": "object",
            "properties": {
                "site": {"type": "string", "description": "Optional site name (e.g. okar, onam, ghaub, agag)"},
            },
            "required": [],
        },
    },
    {
        "name": "get_rainfall",
        "description": "Recent rainfall (30/60/90 days), 7-day forecast, and anomaly vs the long-term normal for a location. Fuses Open-Meteo and NASA POWER with a confidence signal.",
        "parameters": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"}, "lon": {"type": "number"},
            },
            "required": [],
        },
    },
    {
        "name": "estimate_grazing_days",
        "description": "How many days a herd can graze a camp given grass biomass, camp area and herd LSU. Defaults area and LSU from the farmer's records.",
        "parameters": {
            "type": "object",
            "properties": {
                "grass_biomass_kg_ha": {"type": "number"},
                "area_ha": {"type": "number"},
                "herd_lsu": {"type": "number"},
            },
            "required": ["grass_biomass_kg_ha"],
        },
    },
    {
        "name": "get_herd_summary",
        "description": "The farmer's current herd: animal counts by species, total LSU, recent births/sales/deaths. Always use this instead of asking herd size.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_animals",
        "description": "Look up individual animals in the farmer's register by ear tag, name, species, breed or notes.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Tag / name / breed / free text"},
                "species": {"type": "string", "description": "cattle | goat | sheep"},
                "status": {"type": "string", "description": "active | sold | deceased"},
            },
            "required": [],
        },
    },
    {
        "name": "get_upcoming_tasks",
        "description": "Upcoming and overdue vaccinations, treatments and reminders from the farm calendar.",
        "parameters": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Look-ahead window, default 30"}},
            "required": [],
        },
    },
    {
        "name": "log_livestock_event",
        "description": "Record a farm event the farmer mentions: sale, birth, death, vaccination, treatment, weight, or note. Use due_date (YYYY-MM-DD) to schedule a future reminder instead.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_type": {"type": "string", "description": "vaccination | treatment | birth | sale | death | weight | note"},
                "description": {"type": "string"},
                "animal_tag": {"type": "string", "description": "Ear tag or name if it concerns one animal"},
                "event_date": {"type": "string", "description": "YYYY-MM-DD, defaults to today"},
                "due_date": {"type": "string", "description": "YYYY-MM-DD for future reminders"},
            },
            "required": ["event_type", "description"],
        },
    },
    {
        "name": "get_farm_analytics",
        "description": "Twelve-month farm performance: births, sales, deaths, mortality rate, sales revenue, health-calendar compliance, herd structure, stocking versus the regional guideline, and pasture trend. Use for 'how is my farm doing', performance questions, and whenever a trend would strengthen your advice.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_documents",
        "description": "Read documents the farmer uploaded, such as a dosing product label, a vet letter or a grazing lease. Use whenever they refer to 'the document', 'the label', 'the letter' or ask something the uploaded files would answer.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Words to search for"}},
            "required": [],
        },
    },
    {
        "name": "update_animals",
        "description": "Change animal status in the register. Use whenever the farmer says animals were sold, died, or came back into the herd. Give tags if they named specific animals, otherwise give species and count and the tool picks them and tells you which. ALWAYS pair this with log_livestock_event so the sale or loss is recorded too.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "sold | deceased | active"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Ear tags or names, if the farmer named them"},
                "species": {"type": "string", "description": "cattle | goat | sheep, when no tags given"},
                "count": {"type": "integer", "description": "How many animals, when no tags given"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a vaccination or treatment reminder as done when the farmer says they've done it (e.g. 'I did the anthrax shots today').",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Words from the task, e.g. 'anthrax'"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_market_prices",
        "description": "Indicative Namibian livestock auction price ranges. ALWAYS use this before discussing what animals are worth or what to sell. Never quote prices from memory.",
        "parameters": {
            "type": "object",
            "properties": {"species": {"type": "string", "description": "cattle | goat | sheep"}},
            "required": [],
        },
    },
    {
        "name": "register_animal",
        "description": "Add a new animal to the farmer's register (e.g. 'register the new calf, tag W-102').",
        "parameters": {
            "type": "object",
            "properties": {
                "species": {"type": "string", "description": "cattle | goat | sheep | other"},
                "tag": {"type": "string"}, "name": {"type": "string"},
                "breed": {"type": "string"}, "sex": {"type": "string", "description": "male | female"},
                "dob": {"type": "string", "description": "YYYY-MM-DD or year"},
                "notes": {"type": "string"},
            },
            "required": ["species"],
        },
    },
]

_IMPL = {
    "query_rangeland": query_rangeland,
    "compare_seasons": compare_seasons,
    "get_rainfall": get_rainfall,
    "estimate_grazing_days": estimate_grazing_days,
    "get_herd_summary": get_herd_summary,
    "search_animals": search_animals,
    "get_upcoming_tasks": get_upcoming_tasks,
    "log_livestock_event": log_livestock_event,
    "register_animal": register_animal,
    "update_animals": update_animals,
    "complete_task": complete_task,
    "get_market_prices": get_market_prices,
    "read_documents": read_documents,
    "get_farm_analytics": get_farm_analytics,
}


async def execute_tool(name: str, args: Dict[str, Any], user_id: int,
                       profile: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch with profile-based defaults so the agent rarely needs to ask."""
    args = dict(args or {})
    args["user_id"] = user_id

    if name == "query_rangeland" and not args.get("region"):
        args["region"] = profile.get("region") or (
            region_from_latlon(profile["lat"], profile["lon"])
            if profile.get("lat") and profile.get("lon") else "Khomas")
    if name == "compare_seasons" and not args.get("site"):
        args["lat"], args["lon"] = profile.get("lat"), profile.get("lon")
    if name == "get_rainfall":
        if args.get("lat") is None:
            args["lat"] = profile.get("lat")
        if args.get("lon") is None:
            args["lon"] = profile.get("lon")
        if args.get("lat") is None or args.get("lon") is None:
            coords = latlon_from_region(profile.get("region") or "Khomas") or (-22.56, 17.06)
            args["lat"], args["lon"] = coords
    if name == "estimate_grazing_days":
        if not args.get("area_ha") and profile.get("camp_area_ha"):
            args["area_ha"] = profile["camp_area_ha"]
        if not args.get("herd_lsu"):
            args["herd_lsu"] = db.get_herd_summary(user_id)["total_lsu"] or 1.0

    impl = _IMPL.get(name)
    if impl is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await impl(**args)
    except TypeError as e:
        return {"error": f"Bad arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"{name} failed: {e}"}
