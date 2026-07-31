"""Seed a realistic demo farm so every screen looks alive during the demo.

Usage:  .venv/bin/python seed_demo.py
Login:  demo / demo
"""
import datetime
import random

import db
import protocols

USER, PW = "demo", "demo"
TODAY = datetime.date.today()

# Omaheke guideline is ~27 ha/LSU, so 1,800 ha carries roughly 65 LSU.
# Stock the demo farm near capacity, the way a real commercial farm runs.
NAMED_CATTLE = [
    ("NA-0412", "Rooibok", "Brahman", "female", "2019-03"),
    ("NA-0417", "Meisie", "Brahman", "female", "2020-08"),
    ("NA-0428", "Swartkop", "Nguni", "male", "2018-11"),
    ("NA-0440", "Bles", "Brahman", "female", "2022-02"),
    ("NA-0451", "Kleintjie", "Nguni", "female", "2023-04"),
    ("NA-0460", "Nuwe", "Brahman X", "male", "2025-11"),
]
BREEDS = ["Brahman", "Brahman X", "Nguni", "Simbra"]
random.seed(7)
CATTLE = NAMED_CATTLE + [
    (f"NA-{460 + n * 3:04d}", "", random.choice(BREEDS),
     random.choice(["female", "female", "female", "male"]),
     f"{random.choice([2019, 2020, 2021, 2022, 2023, 2024])}-{random.randint(1, 12):02d}")
    for n in range(1, 49)
]
GOATS = [(f"B-{n:02d}", "", "Boer goat", random.choice(["female", "female", "male"])) for n in range(1, 25)]
SHEEP = [(f"D-{n:02d}", "", "Dorper", random.choice(["female", "female", "male"])) for n in range(1, 15)]


def main():
    db.create_user(USER, PW)
    uid = db.verify_user(USER, PW)
    if uid is None:
        raise SystemExit("could not create demo user")

    # Wipe any previous seed so re-running is safe
    with db._conn() as c:
        c.execute("DELETE FROM animals WHERE user_id=?", (uid,))
        c.execute("DELETE FROM animal_events WHERE user_id=?", (uid,))
        c.execute("DELETE FROM farm_logs WHERE user_id=?", (uid,))
        c.execute("DELETE FROM chat_history WHERE user_id=?", (uid,))
        c.commit()

    # Omaheke: real cattle-farming country, and a region with data in both datasets
    db.update_profile(uid, "Omaheke", -21.85, 19.72, 1800, 0, 0, 0,
                      language="en", farm_name="Okatope Farm",
                      full_name="Teofilus Shaduka", role="owner")

    ids = {}
    for tag, name, breed, sex, dob in CATTLE:
        ids[tag] = db.add_animal(uid, tag=tag, name=name, species="cattle",
                                 breed=breed, sex=sex, dob=dob)
    for tag, name, breed, sex in GOATS:
        ids[tag] = db.add_animal(uid, tag=tag, name=name, species="goat", breed=breed, sex=sex)
    for tag, name, breed, sex in SHEEP:
        ids[tag] = db.add_animal(uid, tag=tag, name=name, species="sheep", breed=breed, sex=sex)

    # Animals already out of the herd, so the register and the farm log agree with
    # each other. A log entry saying "sold 6 goats" with six goats still standing in
    # the register is exactly the inconsistency the chat write tools exist to prevent.
    db.update_animal(uid, ids["NA-0428"], status="sold")
    db.update_animal(uid, ids["D-08"], status="deceased")
    sold_goats = [f"B-{n:02d}" for n in range(19, 25)]
    for tag in sold_goats:
        db.update_animal(uid, ids[tag], status="sold")

    # Standard Namibian health calendar
    protocols.apply_protocol(uid, ["cattle", "goat", "sheep"])

    # One overdue item (drives the red alert on the dashboard) and one due this week
    db.add_animal_event(uid, "vaccination",
                        "Anthrax booster for the whole cattle herd (state vet campaign)",
                        due_date=(TODAY - datetime.timedelta(days=9)).isoformat())
    db.add_animal_event(uid, "treatment",
                        "Dose calves for internal parasites after the first rains",
                        animal_id=ids["NA-0460"],
                        due_date=(TODAY + datetime.timedelta(days=5)).isoformat())

    # History so the register reads like a real farm
    history = [
        ("birth", "Heifer calf born to Meisie (NA-0417), healthy", ids["NA-0460"], 70),
        ("sale", "Sold ox NA-0428 at Gobabis auction for N$14,200", ids["NA-0428"], 34),
        ("death", "Ewe D-08 lost to jackal predation near the north fence", ids["D-08"], 21),
        ("weight", "Weighed weaners: average 218 kg", None, 16),
        ("treatment", "Dipped whole herd for ticks", None, 12),
        ("note", "Moved herd from the north camp to the river camp", None, 7),
        ("sale", f"Sold 6 goats at Gobabis to reduce pressure before winter, "
                 f"N$9,600 total ({', '.join(sold_goats)})", None, 26),
    ]
    for etype, desc, aid, days_ago in history:
        db.add_animal_event(uid, etype, desc, animal_id=aid,
                            event_date=(TODAY - datetime.timedelta(days=days_ago)).isoformat(),
                            completed=1)

    for etype, desc, days_ago in [
        ("Pasture Move", "Herd moved to the river camp, north camp resting for six weeks", 7),
        ("Weather Event", "38 mm rain overnight, first good fall of the season", 11),
        ("Livestock Sale", "Sold 6 goats at Gobabis to reduce pressure before winter", 26),
    ]:
        db.add_farm_log(uid, etype, desc)

    herd = db.get_herd_summary(uid)
    print(f"✅ Demo farm ready, login: {USER} / {PW}")
    print(f"   Okatope Farm, Omaheke · 1,800 ha")
    print(f"   Herd: {herd['counts']} = {herd['total_lsu']} LSU ({herd['total_animals']} active animals)")
    print(f"   Upcoming/overdue tasks: {len(db.get_upcoming_events(uid, days=60))}")


if __name__ == "__main__":
    main()
