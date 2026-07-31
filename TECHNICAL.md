# VeldWys: Technical Documentation

DLIX Namibia 2026 Hackathon submission. Companion to [README.md](README.md).

---

## 1. Design decision: the register comes first

The reference architecture for this challenge is *user asks → agent queries dataset → agent answers*. We found the failure mode quickly: every question needs herd size, location and camp area, so either the farmer retypes them constantly or the agent guesses.

We inverted it. The farmer's own data is the first-class citizen, and the agent is a reader/writer of it:

```
Conventional                        VeldWys
─────────────                       ───────
user: "I have 40 cattle on 500ha,   user: "Is my camp overgrazed?"
       is my camp overgrazed?"        └─ agent already knows: 53 cattle,
  └─ agent: dataset lookup                24 goats, 13 sheep = 58.5 LSU,
                                          1,800 ha, Omaheke, plus an
                                          overdue anthrax vaccination
```

Every chat request injects a compact farmer-context block (region, coordinates, camp area, herd summary, overdue/upcoming tasks, recent logs) ahead of the conversation, and the system prompt forbids asking for anything a tool can answer.

The write direction matters as much. `log_livestock_event` and `register_animal` let the farmer maintain records **by talking**: "I sold three goats today" both answers and updates the register. Verified in `test_flow.py`.

---

## 2. Agent loop

`POST /api/chat` (`main.py`):

1. Persist the user message
2. Build messages: system prompt → farmer context → last 12 turns
3. Loop up to 6 iterations:
   - `respond(messages, TOOLS, provider)` → normalized `{text}` or `{tool_calls}`
   - Execute each tool via `execute_tool(name, args, user_id, profile)`
   - Append results, loop
4. Return final text + a trace of every tool call

**Provider abstraction** (`llm.py`): tools are declared once in a neutral JSON-schema dict and converted per provider. OpenAI's `{type:"function"}` shape and Anthropic's `{name, input_schema}` shape. Message history is translated the same way. On any OpenAI failure the same conversation continues on Anthropic mid-flight.

**Profile-based argument defaulting** (`tools.py:execute_tool`) is what makes tool calls cheap and reliable. If the model omits `region`, it's derived from the farmer's map pin; `lat`/`lon` fall back to the pin then the region centroid; `herd_lsu` is computed from the register; `area_ha` comes from the profile. The model can call `query_rangeland` with no arguments at all and still get the right answer.

---

## 3. Data engineering

### 3.1 The real Lacuna dataset

`archive/` contains the actual field forms: 80 cover files, 20 standing-crop files, 20 quantitative files, 15 grazing files across 21 sites and 4 seasons. `prepare_real_data.py` turns them into `data/real_sites.csv` (81 site-season records).

The cover forms are **point-intercept surveys**: 50 sampling points × 8 functional groups (tree, shrub, short shrub, forb, perennial grass, annual grass, litter, bare ground), each scored present/absent, plus grazable (`G`) / non-grazable (`NG`) flags.

The obvious column, `G%`, is `NotApp` on most rows, so using it yields 0.0 everywhere. The real signal is the **presence rate per functional group**:

| Derived metric | Meaning |
|---|---|
| `grass_cover_pct` | perennial + annual grass presence: the forage base |
| `perennial_grass_pct` | perennial grass alone: rangeland health |
| `woody_cover_pct` | tree + shrub presence: **bush encroachment** |
| `bare_ground_pct` | bare ground presence: degradation |
| `palatable_pct` | share of scored hits flagged grazable: forage quality |
| `standing_crop_kg_ha` | clipped-quadrat standing crop (May 2023 visit only) |

Header spelling varies between forms (one file says `Functional groups`), so `normalize()` aliases headers rather than special-casing files.

Because the same sites were visited in **February 2023 and February 2024**, the dataset supports a genuine like-for-like seasonal comparison. Site `agag` went from 41.6% → 9.8% grass cover with bare ground rising 4.0% → 24.9%. That is measured degradation, not a model's guess. `compare_seasons` labels each metric better/worse with the direction of "good" inverted for bush cover and bare ground.

Filenames sort alphabetically (`april_24` before `feb_23`), which would misreport the latest visit, so seasons are ordered explicitly.

### 3.2 Weather fusion

`get_rainfall` calls Open-Meteo, NASA POWER daily, and NASA POWER climatology concurrently (`asyncio.gather`), then:

- **Agreement**: if the two 60-day totals are within 25%, blend and report high confidence; otherwise report the range and drop to moderate. Because dry-season totals sit near zero, an absolute-difference escape hatch (≤ 8 mm) prevents 1 mm vs 6 mm from being called "disagreement".
- **Anomaly**: expected rainfall for the trailing 60 days is built from monthly normals. A percentage is only reported when the normal is ≥ 15 mm; below that the tool returns a dry-season note instead, because "+97% above normal" against a 1.7 mm baseline is noise.
- **Cache**: 6 hours per rounded coordinate, so the dashboard, insights and chat share one call.

### 3.3 Livestock schema

```sql
users        (…, language, farm_name, region, lat, lon, camp_area_ha, quick counts)
animals      (id, user_id, tag, name, species, breed, sex, dob, photo_path, status, notes)
animal_events(id, user_id, animal_id?, event_type, description, event_date, due_date?, completed)
```

Herd counts are **computed** from `animals` where `status='active'`, falling back to the onboarding quick counts if the farmer hasn't entered individuals yet, and `get_herd_summary` reports which source it used. LSU: cattle 1.0, goats/sheep 0.15. An event with a `due_date` and `completed=0` is a reminder; with an `event_date` it's history. One table, both jobs.

---

## 4. The rules engine

`insights.py` runs on dashboard load and costs nothing:

| Rule | Trigger |
|---|---|
| Overdue tasks | any `due_date < today`, not completed → **red** |
| Upcoming tasks | due within 21 days → **amber** |
| Dry season | climatology normal < 15 mm for the window → **amber** advisory |
| Rain forecast | ≥ 15 mm forecast in 7 days → **green** planning prompt |
| Rainfall anomaly | ≤ −40% vs normal → **red**; ≤ −20% → **amber** |
| Grazing countdown | < 30 days → **red**; < 75 → **amber** (suppressed past a season, where forage isn't the binding constraint) |
| Stocking pressure | ha/LSU below 80% of the regional guideline → **amber**/**red** |

Each insight carries a suggested question; tapping it opens the chat with that question already asked. Rules find the problem for free, and the LLM is only paid for when the farmer wants to go deeper.

**Morning briefing** is the one scheduled LLM call: insights + herd + region → four spoken sentences in the farmer's language, then TTS.

---

## 5. Voice

### 5.0 Why Oshiwambo and Otjiherero needed their own number system

The first version sent text straight to the TTS model. Afrikaans came out well. Oshiwambo and Otjiherero did not, and the giveaway was numbers: the sentence was Oshiwambo but "53" and "N$1,500" came out in English.

The obvious fix, asking a model to rewrite the numerals, failed badly. Measured output from `gpt-4o-mini`:

- Oshiwambo: invented words that mean nothing (`omakulu omakumi na oshitatu` for 53)
- Otjiherero: a degenerate repetition loop, sixteen identical clauses, meaning destroyed

Both languages build numbers regularly, so `numerals.py` implements them properly:

```
tens + link + unit           53 -> omilongo ntano na yatatu   (ng)
                                   omirongo vitano na ndatu    (kj)
hundreds/thousands counted   1500 -> eyuvi na omathele yatano  (ng)
                                     eyovi na omasere ndano     (kj)
```

The key realisation is that **nothing needs translating**. The agent already replies *in* the farmer's language, so speech prep only has to convert symbols into words. That makes it pure deterministic Python: instant, free, testable, and correctable by a native speaker editing one table.

`voice.prepare_speech` runs in order: ISO dates to spoken dates, `N$` amounts to amount-plus-currency-words, units (`mm`, `ha`, `LSU`, `kg`, `%`) to their native words, then every remaining number to words. The TTS model then gets per-language accent instructions describing the phonetics it should use (syllable-timed rhythm, pure vowels, full consonant clusters, never clipping final vowels).

The E2E suite asserts no digit survives into Oshiwambo or Otjiherero speech.

**In:** push-to-talk → `whisper-1`, prompt-biased with Namibian farming vocabulary (`kraal`, `veld`, `oshana`, `ozongombe`, `eengobe`) → a `gpt-4o-mini` correction pass that fixes phonetic mangling **without translating**, so the farmer's language is preserved end to end.

**Out:** `gpt-4o-mini-tts`. Voice-initiated questions auto-speak the reply, creating a hands-free loop, which is the realistic mode for someone standing in a camp. Browser `speechSynthesis` covers API failure.

Voice requires HTTPS (`getUserMedia`), which is why the phone demo runs over `tailscale serve` rather than a LAN IP.

---

## 6. Notebook OCR

`POST /api/scan_notebook` sends the photo to `claude-sonnet-5` with a strict JSON schema. Measured on a handwritten Afrikaans page: correct ear tags, species inferred from breed words (*Boerbok* → goat, *Dorper* → sheep), sex inferred from *koei*/*ooi*/*bok*, and uncertainty preserved (`"mank? (mogelijk kreupel)"`). ~13 s per page.

**Nothing is saved automatically.** The farmer gets an editable review screen and confirms before anything is written. OCR on handwriting is probabilistic, and a livestock register is a legal document under NamLITS traceability.

---

## 6.5 The chat writes to the farm

The round-one agent could read the register but not change it, so "I sold three goats" produced a log line while the herd count stayed put. That is the gap between a chatbot and a farm system.

`update_animals` and `complete_task` close it. The system prompt makes a sale or death always do two things, change the animal statuses and log the event, and `update_animals` returns exactly which tags it touched so the agent can read them back and be corrected. When no ear tags are named it picks the oldest untagged animals of that species first, so identified animals are never silently reassigned.

This also enables the daily debrief: a farmer narrates the day in one message, the agent makes every write, then summarises what it filed.

## 7. Offline

Rural Namibian farms have poor connectivity, so this is a requirement rather than a nicety.

- **Service worker** caches the app shell (cache-first, network-refresh). API calls are never cached by the worker, the app manages its own data cache so it controls freshness.
- **Render-from-cache-then-refresh**: every screen paints from `localStorage` immediately, then updates when the network answers.
- **Write queue**: `post()` catches offline failures and queues the request; `syncQueue()` replays on the `online` event. Adding an animal in a camp with no signal works, and syncs on the way home.
- **Degradation is explicit**: register and dashboard work offline; chat and voice say they need a connection rather than failing silently.
- **Installable**: manifest + icons, so "Add to Home Screen" gives a full-screen app.

---

## 8. Verification

`test_flow.py` covers signup → onboarding (asserting region derivation from coordinates) → animal registration → protocol application → overdue reminders → insights → CSV export → five agent questions → confirmation that a conversational "I sold 3 goats" actually landed in the register → morning briefing.

Manually verified: onboarding in all four languages, voice round-trip on the phone over Tailscale HTTPS, notebook scan, offline dashboard with queued writes, and provider failover by revoking the OpenAI key mid-session.

---

## 8.5 Analytics

`analytics.py` computes, with no model calls, so the tab is free and works from cache:

| Metric | Why a farmer cares |
|---|---|
| Stocking vs regional guideline | The core question of this hackathon, stated as a percentage of what the land is guided to carry |
| Grazing days remaining | Forage math from their own herd LSU and camp size |
| Herd movement by month | Births, sales and deaths, and the net change they add up to |
| Mortality share | Losses as a share of all herd changes, the number that should worry them |
| Health-calendar compliance | How much of the vaccination schedule is actually being kept |
| Sales revenue | Parsed from `N$` amounts recorded against sale events |
| Real pasture trend | Grass cover, bare ground and bush cover across the four 2023-24 field visits at the nearest monitoring site |

The same numbers are exposed to the agent through `get_farm_analytics`, so it can say "your herd shrank while your grazing days fell" instead of guessing.

Charts are inline SVG with no chart library, which keeps them working offline. The categorical palette was checked with a colour-blind separation validator before use: green and orange are deliberately non-adjacent because that is the weak pair under protanopia.

## 9. Limitations

- The synthetic starter dataset drives regional carrying-capacity figures; the real field data covers 21 monitoring sites, so neither is a measurement of any particular farm's camp. The agent says so.
- Standing-crop measurements exist only for the May 2023 visit, so the year-over-year comparison rests on cover metrics.
- Vaccination protocols are general Namibian practice, not veterinary prescription, timings should be confirmed with the local state vet.
- Auth is username/password with SHA-256 hashing and no session tokens: appropriate for a hackathon prototype, not production. Real deployment needs salted hashing (bcrypt/argon2) and proper sessions.
- Whisper handles Oshiwambo and Otjiherero far less reliably than English or Afrikaans; the correction pass helps but a fine-tuned local model is the real answer.
- The Oshiwambo and Otjiherero numeral tables and the accent instructions are our best effort and want a native speaker's review. They are isolated in `numerals.py` and `voice.py` precisely so that review is a small edit.
- Conversation mode uses a hand-rolled RMS voice-activity detector. A wasm VAD such as Silero would be more robust in wind and background noise, but it needs remote assets that would break the offline-first build.
- Market prices are static indicative ranges, not a live auction feed. The agent is required to say so.

## 10. Next

Community-level grazing coordination for communal conservancies, SMS/WhatsApp channel for feature phones, camp-level (not farm-level) rotation planning, NamLITS API integration, and fine-tuned ASR for Namibian languages.
