"""Proactive insight engine: pure rules, zero LLM cost.

Runs on dashboard load. Each insight carries a translation `key` plus `vars`, so the
front-end renders it in the farmer's language without a translation API call.
English `title`/`detail`/`question` are also returned as a fallback and for the
morning-briefing prompt.
"""
import datetime
from typing import List, Dict, Any

import db
import tools


def _mk(key: str, severity: str, icon: str, title: str, detail: str,
        question: str, **vars_) -> Dict[str, Any]:
    return {"key": key, "severity": severity, "icon": icon, "title": title,
            "detail": detail, "question": question, "vars": vars_}


async def compute_insights(user_id: int) -> List[Dict[str, Any]]:
    profile = db.get_profile(user_id) or {}
    herd = db.get_herd_summary(user_id)
    out: List[Dict[str, Any]] = []

    # 1. Vaccinations / treatments due or overdue
    upcoming = db.get_upcoming_events(user_id, days=21)
    overdue = [e for e in upcoming if e["overdue"]]
    soon = [e for e in upcoming if not e["overdue"]]
    if overdue:
        first = overdue[0]
        out.append(_mk(
            "overdue", "red", "💉",
            f"{len(overdue)} overdue task{'s' if len(overdue) > 1 else ''}",
            f"{first['description'][:90]} was due {first['due_date']}.",
            "Which vaccinations or treatments are overdue and what should I do first?",
            n=len(overdue), what=first["description"][:90], date=first["due_date"]))
    elif soon:
        first = soon[0]
        out.append(_mk(
            "due_soon", "amber", "💉",
            f"{len(soon)} task{'s' if len(soon) > 1 else ''} due in the next 3 weeks",
            f"Next: {first['description'][:90]} (due {first['due_date']}).",
            "What vaccinations are coming up and how should I prepare?",
            n=len(soon), what=first["description"][:90], date=first["due_date"]))

    # 2. Weather-driven checks (6h-cached fusion call, shared with the chat agent)
    lat, lon = profile.get("lat"), profile.get("lon")
    weather = None
    if lat and lon:
        try:
            weather = await tools.get_rainfall(lat, lon)
        except Exception:
            weather = None

    if weather and not weather.get("error"):
        anomaly = weather.get("anomaly_vs_normal_pct")
        rain60 = weather.get("rain_60_mm")
        forecast = weather.get("forecast_7d_mm")

        # Dry season: a percentage anomaly is meaningless against a near-zero normal,
        # but the farmer still needs to know the veld will not regrow yet.
        if weather.get("season_note"):
            out.append(_mk(
                "dry_season", "amber", "☀️",
                "Dry season, no regrowth expected",
                (f"About {rain60 if rain60 is not None else 0} mm fell in the last 60 days, which is "
                 "normal for this time of year. Your grazing has to last on standing grass until the rains return."),
                "It's the dry season, how do I make my grazing last until the rains?",
                mm=rain60 if rain60 is not None else 0))
        if isinstance(forecast, (int, float)) and forecast >= 15:
            out.append(_mk(
                "rain_coming", "green", "🌦️",
                f"{forecast:.0f} mm rain forecast this week",
                "Good rain is coming. Plan camp rotation so the rested veld gets the benefit.",
                "Rain is forecast this week, how should I plan my grazing around it?",
                mm=round(forecast)))
        if anomaly is not None and anomaly <= -40:
            out.append(_mk(
                "drought", "red", "🌧️",
                "Rainfall well below normal",
                (f"Last 60 days: {rain60} mm, {abs(anomaly):.0f}% below the long-term normal. Drought risk."),
                "Rainfall is far below normal, should I reduce my herd or move them, and when?",
                mm=rain60, pct=abs(round(anomaly))))
        elif anomaly is not None and anomaly <= -20:
            out.append(_mk(
                "dry", "amber", "🌧️",
                "Rainfall below normal",
                f"Last 60 days about {abs(anomaly):.0f}% below normal. Watch grazing reserves.",
                "Given the below-normal rainfall, how long can my herd stay on this pasture?",
                pct=abs(round(anomaly))))

    # 3. Grazing countdown + stocking pressure vs regional carrying capacity
    region = profile.get("region")
    area = profile.get("camp_area_ha") or 0
    lsu = herd.get("total_lsu") or 0
    if region and area > 0 and lsu > 0 and not tools.df_rangeland.empty:
        try:
            land = await tools.query_rangeland(region)
            if "summary" in land:
                biomass = float(land["summary"]["avg_grass_biomass_kg_ha"])
                graze = await tools.estimate_grazing_days(biomass, area, lsu)
                days = graze.get("days_remaining")
                if isinstance(days, (int, float)) and days < 270:
                    if days < 30:
                        out.append(_mk(
                            "graze_low", "red", "🌾",
                            f"~{days:.0f} grazing days left",
                            (f"At regional biomass (~{biomass:.0f} kg/ha) your {lsu} LSU herd "
                             "exhausts this camp soon."),
                            "My grazing is running out, should I move the herd, and roughly when?",
                            days=round(days), biomass=round(biomass), lsu=lsu))
                    elif days < 75:
                        out.append(_mk(
                            "graze_watch", "amber", "🌾",
                            f"~{days:.0f} grazing days left",
                            "Plan the next camp move or a rest rotation now.",
                            "How should I plan my next pasture rotation?",
                            days=round(days)))
                cc = float(land["summary"]["avg_carrying_capacity_ha_per_lsu"])
                have = area / lsu
                if have < cc * 0.8:
                    out.append(_mk(
                        "overstocked", "amber" if have > cc * 0.5 else "red", "⚖️",
                        "Stocking above regional capacity",
                        (f"You have {have:.1f} ha per LSU; the {region} guideline is about "
                         f"{cc:.0f} ha/LSU."),
                        "Is my camp overstocked, and what is a safe stocking rate right now?",
                        have=round(have, 1), guide=round(cc), region=region))
        except Exception:
            pass

    if not out:
        out.append(_mk("all_clear", "green", "✅", "All clear",
                       "No urgent tasks or warnings. Herd register and calendar look healthy.",
                       "Give me a quick status report on my farm."))
    return out
