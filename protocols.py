"""Standard Namibian livestock vaccination and health protocols.

Static domain knowledge turned into dated reminders, so it costs nothing to run.
Each item carries a stable `key` that the front-end uses to show the reminder in the
farmer's own language (see PROTO_* entries in static/i18n.js). The English text stays
in the database for the agent's context.

Timings follow common Namibian practice: core vaccinations land before the rainy
season. Confirm dates with the local state vet or extension officer.
"""
import datetime
from typing import List, Dict, Any

import db

PROTOCOLS: Dict[str, List[Dict[str, Any]]] = {
    "cattle": [
        {"key": "anthrax", "month": 10, "name": "Anthrax vaccination",
         "desc": "Yearly anthrax shot, before the rains. Compulsory in many districts."},
        {"key": "botulism", "month": 10, "name": "Botulism vaccination",
         "desc": "Yearly botulism (lamsiekte) shot, often combined with anthrax and blackquarter."},
        {"key": "blackleg", "month": 10, "name": "Blackquarter vaccination",
         "desc": "Yearly blackquarter shot for young cattle before the rains."},
        {"key": "lsd", "month": 9, "name": "Lumpy skin disease vaccination",
         "desc": "Yearly lumpy skin shot before the mosquitoes come out."},
        {"key": "brucella", "month": 6, "name": "Brucellosis (heifers 4 to 8 months)",
         "desc": "Once-off brucellosis shot for heifer calves between four and eight months."},
        {"key": "parasites", "month": 12, "name": "Dose and dip for parasites",
         "desc": "Dose and dip at the start of the rains, then check again mid season."},
    ],
    "goat": [
        {"key": "pulpy", "month": 9, "name": "Pulpy kidney vaccination",
         "desc": "Yearly pulpy kidney shot before the green flush."},
        {"key": "pasteurella", "month": 9, "name": "Pasteurella vaccination",
         "desc": "Yearly pasteurella and pneumonia shot."},
        {"key": "parasites", "month": 12, "name": "Dose for internal parasites",
         "desc": "Dose for worms when the rains start, check again mid season."},
    ],
    "sheep": [
        {"key": "pulpy", "month": 9, "name": "Pulpy kidney vaccination",
         "desc": "Yearly pulpy kidney shot before the green flush."},
        {"key": "bluetongue", "month": 8, "name": "Bluetongue vaccination",
         "desc": "Yearly bluetongue shot before midge season."},
        {"key": "parasites", "month": 12, "name": "Dose for internal parasites",
         "desc": "Dose for worms when the rains start."},
    ],
}


def _next_occurrence(month: int) -> str:
    """The next 15th of `month` that hasn't passed yet."""
    today = datetime.date.today()
    year = today.year
    if month < today.month or (month == today.month and today.day > 15):
        year += 1
    return datetime.date(year, month, 15).isoformat()


def apply_protocol(user_id: int, species_list: List[str]) -> Dict[str, Any]:
    created = []
    for species in species_list:
        for item in PROTOCOLS.get(species, []):
            due = _next_occurrence(item["month"])
            db.add_animal_event(
                user_id,
                event_type="vaccination" if "vaccination" in item["name"].lower() else "treatment",
                description=f"[{species}] {item['name']}. {item['desc']}",
                due_date=due,
                tkey=f"proto_{species}_{item['key']}",
            )
            created.append({"species": species, "name": item["name"], "due": due})
    return {"created": len(created), "reminders": created}
