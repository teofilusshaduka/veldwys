"""Farm analytics: the numbers a livestock farmer actually makes decisions on.

Everything here is computed from the farmer's own records plus the rangeland and
weather data the agent already uses. No LLM calls, so the tab is free to open and
works from cache when there's no signal.

The agent reads the same output through the get_farm_analytics tool, which lets it
say things like "your herd grew 8% but your grazing days fell" instead of guessing.
"""
import datetime
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional

import db
import tools

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _month_key(iso: str) -> Optional[str]:
    try:
        return iso[:7]
    except Exception:
        return None


def _money_in(text: str) -> float:
    """Pull N$ amounts out of an event description, e.g. 'sold for N$14,200'."""
    total = 0.0
    for m in re.finditer(r"N\$\s*([\d][\d,\s]*(?:\.\d+)?)", text or ""):
        try:
            total += float(m.group(1).replace(",", "").replace(" ", ""))
        except ValueError:
            pass
    return total


def herd_movement(user_id: int, months: int = 12) -> Dict[str, Any]:
    """Births, sales and deaths per month, and the net change they add up to."""
    events = db.get_animal_events(user_id, limit=2000)
    today = datetime.date.today().replace(day=1)
    keys, labels = [], []
    for i in range(months - 1, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year + ((today.month - i - 1) // 12)
        keys.append(f"{y:04d}-{m:02d}")
        labels.append(MONTH_LABELS[m - 1])

    series = {k: defaultdict(int) for k in ("birth", "sale", "death")}
    revenue = defaultdict(float)
    for e in events:
        kind = e["event_type"]
        when = _month_key(e.get("event_date") or e.get("created_at") or "")
        if not when or when not in keys:
            continue
        if kind in series:
            series[kind][when] += 1
        if kind == "sale":
            revenue[when] += _money_in(e.get("description", ""))

    births = [series["birth"][k] for k in keys]
    sales = [series["sale"][k] for k in keys]
    deaths = [series["death"][k] for k in keys]
    return {
        "labels": labels,
        "births": births, "sales": sales, "deaths": deaths,
        "revenue": [round(revenue[k]) for k in keys],
        "net_change": sum(births) - sum(sales) - sum(deaths),
        "total_births": sum(births), "total_sales": sum(sales), "total_deaths": sum(deaths),
        "total_revenue": round(sum(revenue.values())),
        # Losing animals to death is the number that should worry a farmer
        "mortality_pct": round(100 * sum(deaths) / max(1, sum(births) + sum(sales) + sum(deaths)), 1),
    }


def health_compliance(user_id: int) -> Dict[str, Any]:
    """How much of the health calendar is actually being kept."""
    events = db.get_animal_events(user_id, limit=2000)
    scheduled = [e for e in events if e.get("due_date")]
    done = [e for e in scheduled if e["completed"]]
    today = datetime.date.today().isoformat()
    overdue = [e for e in scheduled if not e["completed"] and e["due_date"] < today]
    return {
        "scheduled": len(scheduled),
        "completed": len(done),
        "overdue": len(overdue),
        "compliance_pct": round(100 * len(done) / len(scheduled), 0) if scheduled else None,
        "overdue_items": [{"what": e["description"][:70], "due": e["due_date"]} for e in overdue[:5]],
    }


def herd_structure(user_id: int) -> Dict[str, Any]:
    """Composition and breeding structure. Female share drives future growth."""
    animals = db.get_animals(user_id, status="active")
    by_species = defaultdict(int)
    females = defaultdict(int)
    ages = []
    today = datetime.date.today()
    for a in animals:
        by_species[a["species"]] += 1
        if (a.get("sex") or "").lower() == "female":
            females[a["species"]] += 1
        dob = (a.get("dob") or "").strip()
        m = re.match(r"(\d{4})", dob)
        if m:
            ages.append(today.year - int(m.group(1)))
    cattle = by_species.get("cattle", 0)
    return {
        "by_species": dict(by_species),
        "females": dict(females),
        "female_pct_cattle": round(100 * females.get("cattle", 0) / cattle, 0) if cattle else None,
        "avg_age_years": round(sum(ages) / len(ages), 1) if ages else None,
        "tagged_pct": round(100 * sum(1 for a in animals if (a.get("tag") or "").strip()) / len(animals), 0) if animals else None,
        "total_active": len(animals),
    }


async def grazing_position(user_id: int, profile: Dict[str, Any]) -> Dict[str, Any]:
    """Where this farm sits against its regional grazing guideline."""
    herd = db.get_herd_summary(user_id)
    lsu = herd.get("total_lsu") or 0
    area = profile.get("camp_area_ha") or 0
    region = profile.get("region")
    out: Dict[str, Any] = {"lsu": lsu, "area_ha": area, "region": region}
    if not (region and area and lsu):
        return out
    try:
        land = await tools.query_rangeland(region)
        if "summary" not in land:
            return out
        s = land["summary"]
        guideline = float(s["avg_carrying_capacity_ha_per_lsu"])
        actual = area / lsu
        graze = await tools.estimate_grazing_days(float(s["avg_grass_biomass_kg_ha"]), area, lsu)
        out.update({
            "ha_per_lsu": round(actual, 1),
            "guideline_ha_per_lsu": round(guideline, 1),
            # Above 100% means carrying more animals than the region suggests
            "stocking_vs_guideline_pct": round(100 * guideline / actual, 0) if actual else None,
            "capacity_lsu": round(area / guideline, 1) if guideline else None,
            "grazing_days": graze.get("days_remaining"),
            "biomass_kg_ha": round(float(s["avg_grass_biomass_kg_ha"])),
            "bush_encroachment": s.get("common_bush_encroachment"),
        })
    except Exception:
        pass
    return out


async def rainfall_series(profile: Dict[str, Any]) -> Dict[str, Any]:
    lat, lon = profile.get("lat"), profile.get("lon")
    if not (lat and lon):
        return {}
    try:
        w = await tools.get_rainfall(lat, lon)
        if w.get("error"):
            return {}
        return {
            "rain_30_mm": w.get("rain_30_mm"), "rain_60_mm": w.get("rain_60_mm"),
            "rain_90_mm": w.get("rain_90_mm"), "normal_60d_mm": w.get("normal_60d_mm"),
            "anomaly_pct": w.get("anomaly_vs_normal_pct"),
            "forecast_7d_mm": w.get("forecast_7d_mm"),
            "confidence": w.get("confidence"), "season_note": w.get("season_note"),
        }
    except Exception:
        return {}


async def pasture_trend(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Real measured pasture change at the monitoring site nearest this farm."""
    lat, lon = profile.get("lat"), profile.get("lon")
    try:
        res = await tools.compare_seasons(lat=lat, lon=lon)
        site = (res.get("sites") or [{}])[0]
        if not site.get("site"):
            return {}
        import pandas as pd
        g = tools.df_real[tools.df_real["site"] == site["site"]].set_index("season")
        order = [s for s in tools.SEASON_ORDER if s in g.index]
        pick = lambda col: [round(float(g.loc[s, col]), 1) if pd.notna(g.loc[s, col]) else None
                            for s in order]
        return {
            "site": site["site"],
            "labels": [tools.SEASON_LABELS[s] for s in order],
            "grass_cover": pick("grass_cover_pct"),
            "bare_ground": pick("bare_ground_pct"),
            "woody_cover": pick("woody_cover_pct"),
            "comparison": site.get("same_season_comparison"),
            "source": "Real field measurements, Namibia Rangeland & Pasture Dataset",
        }
    except Exception:
        return {}


async def compute(user_id: int) -> Dict[str, Any]:
    profile = db.get_profile(user_id) or {}
    return {
        "movement": herd_movement(user_id),
        "health": health_compliance(user_id),
        "structure": herd_structure(user_id),
        "grazing": await grazing_position(user_id, profile),
        "rainfall": await rainfall_series(profile),
        "pasture": await pasture_trend(profile),
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }


async def summary_for_agent(user_id: int) -> Dict[str, Any]:
    """A compact version the agent can reason over without blowing the context."""
    full = await compute(user_id)
    m, h, s, g = full["movement"], full["health"], full["structure"], full["grazing"]
    return {
        "herd": {"active": s.get("total_active"), "by_species": s.get("by_species"),
                 "female_pct_cattle": s.get("female_pct_cattle"),
                 "avg_age_years": s.get("avg_age_years")},
        "last_12_months": {"births": m["total_births"], "sales": m["total_sales"],
                           "deaths": m["total_deaths"], "net_change": m["net_change"],
                           "mortality_pct": m["mortality_pct"],
                           "sales_revenue_N$": m["total_revenue"]},
        "health_calendar": {"compliance_pct": h["compliance_pct"], "overdue": h["overdue"]},
        "grazing": {"ha_per_lsu": g.get("ha_per_lsu"),
                    "regional_guideline_ha_per_lsu": g.get("guideline_ha_per_lsu"),
                    "stocking_vs_guideline_pct": g.get("stocking_vs_guideline_pct"),
                    "grazing_days": g.get("grazing_days")},
        "pasture_trend": full["pasture"].get("comparison"),
        "rainfall": full["rainfall"],
    }
