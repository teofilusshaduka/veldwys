"""End-to-end check of the VeldWys API against a running server (port 8001)."""
import asyncio
import httpx

import db
import voice

BASE = "http://127.0.0.1:8001"
USER = "e2e_farmer"


def reset(uid: int):
    """Keep the test idempotent, wipe this user's records before each run."""
    with db._conn() as conn:
        for table in ("animals", "animal_events", "farm_logs", "chat_history", "chats", "documents"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (uid,))
        conn.commit()


def check(label, ok, detail=""):
    print(f"   {'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    return ok


async def main():
    failures = []
    async with httpx.AsyncClient(base_url=BASE, timeout=120) as c:
        print("\n=== setup ===")
        await c.post("/api/signup", json={"username": USER, "password": "pw"})
        uid = (await c.post("/api/login", json={"username": USER, "password": "pw"})).json()["user_id"]
        reset(uid)
        r = await c.post(f"/api/profile?user_id={uid}", json={
            "farm_name": "Okatope Test Farm", "full_name": "Test Farmer", "role": "owner",
            "language": "en", "lat": -21.8, "lon": 19.7, "camp_area_ha": 1200,
            "cattle_count": 0, "goat_count": 0, "sheep_count": 0})
        failures += [] if check("region derived from map pin", r.json()["region"] == "Omaheke",
                                r.json()["region"]) else ["region"]

        for tag, sp in [("NA-0417", "cattle"), ("NA-0418", "cattle"), ("NA-0419", "cattle"),
                        ("G-21", "goat"), ("G-22", "goat"), ("G-23", "goat"), ("G-24", "goat"),
                        ("S-07", "sheep")]:
            await c.post(f"/api/animals?user_id={uid}", json={"tag": tag, "species": sp, "sex": "female"})
        await c.post(f"/api/protocols/apply?user_id={uid}", json={"species": ["cattle", "goat", "sheep"]})
        await c.post(f"/api/events?user_id={uid}", json={
            "event_type": "vaccination", "description": "Anthrax booster for the cattle",
            "due_date": "2026-07-01"})

        print("\n=== numerals (spoken native numbers) ===")
        ng = await voice.prepare_speech(None, "53 cattle and N$1500", "ng")
        kj = await voice.prepare_speech(None, "53 cattle and N$1500", "kj")
        failures += [] if check("Oshiwambo has no digits left", not any(ch.isdigit() for ch in ng), ng[:60]) else ["ng"]
        failures += [] if check("Otjiherero has no digits left", not any(ch.isdigit() for ch in kj), kj[:60]) else ["kj"]

        print("\n=== agent updates the herd from chat ===")
        before = db.get_herd_summary(uid)["counts"].get("goat", 0)
        r = await c.post("/api/chat", json={"message": "I sold 3 goats at the auction today", "user_id": uid})
        d = r.json()
        after = db.get_herd_summary(uid)["counts"].get("goat", 0)
        failures += [] if check("goats marked sold in the register", after == before - 3,
                                f"{before} -> {after}") else ["sale"]
        failures += [] if check("both tools used", {"update_animals", "log_livestock_event"} <=
                                {t["name"] for t in d.get("trace", [])},
                                str([t["name"] for t in d.get("trace", [])])) else ["tools"]

        print("\n=== agent completes a task from chat ===")
        open_before = len(db.find_open_events(uid, limit=200))
        r = await c.post("/api/chat", json={"message": "I did the anthrax booster this morning", "user_id": uid})
        open_after = len(db.find_open_events(uid, limit=200))
        failures += [] if check("a reminder was closed", open_after == open_before - 1,
                                f"{open_before} -> {open_after}") else ["complete_task"]

        print("\n=== prices are grounded, not invented ===")
        r = await c.post("/api/chat", json={"message": "What are my goats worth?", "user_id": uid})
        d = r.json()
        failures += [] if check("get_market_prices was called",
                                "get_market_prices" in {t["name"] for t in d.get("trace", [])}) else ["prices"]

        print("\n=== chats ===")
        cid = (await c.post(f"/api/chats?user_id={uid}")).json()["id"]
        await c.post("/api/chat", json={"message": "Is my camp overgrazed?", "user_id": uid, "chat_id": cid})
        chats = (await c.get(f"/api/chats?user_id={uid}")).json()
        failures += [] if check("chat created and titled", any(x["id"] == cid and x["title"] for x in chats)) else ["chats"]
        found = (await c.get(f"/api/chats?user_id={uid}&q=overgrazed")).json()
        failures += [] if check("chat search finds message text", len(found) >= 1) else ["chat search"]

        print("\n=== documents ===")
        files = {"file": ("dip.txt", b"TICKGUARD DIP. Mix 10 ml per 10 litres of water. "
                                     b"Withdrawal period 21 days before slaughter.", "text/plain")}
        r = await c.post(f"/api/documents?user_id={uid}", files=files)
        failures += [] if check("document uploaded", r.status_code == 200) else ["doc upload"]
        r = await c.post("/api/chat", json={"message": "What is the withdrawal period on the dip I uploaded?",
                                            "user_id": uid})
        d = r.json()
        failures += [] if check("agent read the document",
                                "read_documents" in {t["name"] for t in d.get("trace", [])} or
                                "21" in d["text"]) else ["doc read"]

        print("\n=== analytics ===")
        a = (await c.get(f"/api/analytics?user_id={uid}")).json()
        failures += [] if check("analytics computed", "movement" in a and "grazing" in a) else ["analytics"]
        failures += [] if check("sale counted in movement", a["movement"]["total_sales"] >= 1,
                                str(a["movement"]["total_sales"])) else ["movement"]

        print("\n=== translation + voice ===")
        r = (await c.post("/api/translate_chat", json={"texts": ["Your camp is not overgrazed."], "lang": "af"})).json()
        failures += [] if check("chat translated", r["texts"][0] != "Your camp is not overgrazed.",
                                r["texts"][0]) else ["translate"]
        r = await c.post("/api/tts", json={"text": "Oongombe 53.", "lang": "ng", "gender": "male"})
        failures += [] if check("Oshiwambo male TTS returns audio",
                                r.status_code == 200 and len(r.content) > 5000) else ["tts"]

        print("\n=== brief questions ===")
        for q in ["Is my camp overgrazed?",
                  "How does my pasture compare to the same time last year?",
                  "How is my farm performing this year?"]:
            d = (await c.post("/api/chat", json={"message": q, "user_id": uid})).json()
            tools_used = [t["name"] for t in d.get("trace", [])]
            print(f"   {q}\n      tools: {tools_used}\n      {d['text'][:150]}")

    print("\n" + ("ALL CHECKS PASSED" if not failures else f"FAILURES: {failures}"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
