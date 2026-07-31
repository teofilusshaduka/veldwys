# 🐄 VeldWys

**An AI rangeland advisor that already knows your herd.**

*Deep Learning IndabaX Namibia 2026 Hackathon: Building an AI Agent for Rangeland & Livestock Advisory*

---

## The problem we actually solved

The brief asks for an agent that turns rangeland data into grazing advice. We built that, and then fixed the thing that would have made it useless in practice.

A chatbot that asks *"how many cattle do you have?"* every single conversation is not an advisor; it's a form with a personality. Real farm advice depends on knowing the herd, the camp, the vaccination calendar, and what happened last month. So VeldWys is a **livestock management system with an AI agent on top of it**. The agent reads the farmer's own register before it answers, and it can write to that register when the farmer says *"I sold three goats today."*

The livestock register isn't a hypothetical either. Our team farms; the herd is tracked in a paper notebook. So VeldWys can **photograph that notebook and read it in**, Afrikaans handwriting included.

---

## What it does

**Everything the brief asks for**
- Agentic tool-calling over the rangeland dataset. The model decides when to query data, weather, or the farm register
- Live weather from **two** APIs (Open-Meteo + NASA POWER) fused with an agreement/confidence signal
- Plain-language recommendations that state their reasoning and cite the actual numbers
- Conversational web UI, mobile-first
- **Bonus:** speech-to-text *and* text-to-speech

**Plus what makes it genuinely useful**
- **Livestock register** of individual animals: ear tags, breed, sex, birth date, photos, status (active/sold/deceased)
- **Health calendar** with Namibian vaccination protocols auto-scheduled (anthrax, botulism, blackquarter, lumpy skin, brucellosis, pulpy kidney, bluetongue)
- **Proactive alerts** for overdue vaccinations, drought and dry-season warnings, a grazing-days countdown, and stocking pressure against regional capacity. Computed by rules, so they cost nothing and work every time the dashboard opens.
- **Morning briefing**: a spoken summary of what needs attention today, in the farmer's language
- **Notebook scanning**: photograph a page of handwritten records, check what was read, save it to the register
- **Four languages**: English, Afrikaans, Oshiwambo and Otjiherero across the whole interface, not just the chat
- **Works offline** as an installable app. The register and dashboard open without signal, and anything you record queues until you are back online
- **The chat keeps the records.** Say "I sold three goats at the auction" and it marks three goats sold, names the tags it chose, and logs the sale. Say "I did the anthrax shots" and it closes that reminder. A farmer never has to open a form.
- **Daily debrief.** Talk through the whole day in one go and it files every piece of it.
- **Conversation mode**, a hands-free back-and-forth. It listens, answers out loud, and starts listening again.
- **Chat management** with multiple conversations, full-text search, and document upload
- **Farm insights tab** with stocking against regional capacity, herd movement, sales revenue, health-calendar compliance, rainfall, and real measured pasture trend
- **NamLITS-style CSV export** of the herd register

---

## Data sources

| Source | Use |
|---|---|
| **Namibia's Rangeland & Pasture Dataset** (Lacuna Fund / UNAM / Farm4Trade): the real field forms | Ground-measured vegetation cover, perennial grass, bush encroachment, bare ground and standing crop from **21 monitoring sites**, visited Feb 2023, May 2023, Feb 2024, April 2024. Powers genuine **same-season year-over-year** comparison. |
| Synthetic starter dataset (1,200 sites, 14 regions) | Regional carrying capacity, biomass, grazing pressure and tenure comparison for any region a farmer pins |
| **Open-Meteo** | 90-day rainfall history + 7-day forecast |
| **NASA POWER** | Independent rainfall cross-check + long-term climatology normals |

The agent always reports which source answered. When the two weather APIs disagree it reports a range instead of silently averaging them.

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

Build the real-dataset extract (the `archive/` field forms ship with the repo):

```bash
python prepare_real_data.py
```

Seed a realistic demo farm with 90 animals, a health calendar and one overdue vaccination:

```bash
python seed_demo.py
```

Run it:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Open <http://localhost:8001> and sign in with **demo / demo**.

### Running it on a phone

Voice needs HTTPS. Over Tailscale:

```bash
tailscale serve --bg 8001
```

That gives a real certificate on your tailnet, so the microphone and "Add to Home Screen" both work on the phone.

---

## How it's built

```
Farmer (phone / laptop, works offline)
        │
        ▼
┌──────────────────────────────────────────────┐
│  PWA: 4 languages, voice in/out, offline     │
│  cache + write queue, installable            │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│  FastAPI                                     │
│                                              │
│  Rules engine (free)      LLM router         │
│  · overdue tasks          primary: gpt-4o-mini│
│  · drought / dry season   fallback: claude-haiku-4-5
│  · grazing countdown      (auto-failover)    │
│  · stocking pressure               │         │
│                                    ▼         │
│                          14 agent tools      │
│   ┌──────────────┬───────────────┬─────────┐ │
│   │ Rangeland    │ Weather       │ Farm    │ │
│   │ · synthetic  │ Open-Meteo    │ register│ │
│   │ · REAL field │   +           │ (read & │ │
│   │   2023-24    │ NASA POWER    │  write) │ │
│   │              │ fused         │         │ │
│   └──────────────┴───────────────┴─────────┘ │
└──────────────────────────────────────────────┘
                    │
              SQLite: farm, animals, events, chat
```

### The fourteen tools

| Tool | What it does |
|---|---|
| `query_rangeland` | Regional pasture condition; optional communal vs commercial vs conservancy comparison |
| `compare_seasons` | **Real** Feb-2023 vs Feb-2024 field measurements at the nearest monitoring site |
| `get_rainfall` | Fused Open-Meteo + NASA POWER, with confidence and climatology anomaly |
| `estimate_grazing_days` | Forage math from the farmer's actual herd LSU and camp size |
| `get_herd_summary` | Counts by species, total LSU, recent births/sales/deaths |
| `search_animals` | Look up individual animals by tag, name, breed |
| `get_upcoming_tasks` | Vaccinations and treatments due or overdue |
| `log_livestock_event` | **Writes**: records sales, births, deaths and treatments from conversation |
| `register_animal` | **Writes**: adds an animal to the register from conversation |
| `update_animals` | **Writes**: marks animals sold or deceased and reports exactly which tags changed |
| `complete_task` | **Writes**: closes a vaccination or treatment reminder when the farmer says it's done |
| `get_market_prices` | Indicative Namibian auction ranges, so prices are never invented |
| `read_documents` | Reads product labels, vet letters and leases the farmer uploaded |
| `get_farm_analytics` | Twelve-month performance so advice can cite real trends |

### Models and cost

| Job | Model | Why |
|---|---|---|
| Chat agent | `gpt-4o-mini` | Cheap enough that a full demo day costs cents |
| Failover | `claude-haiku-4-5` | Different provider, same cost tier, and it survives an outage mid-conversation |
| Speech-to-text | `whisper-1` + `gpt-4o-mini` correction pass | Whisper prompt-biased with Namibian farming vocabulary, then cleaned up without translating |
| Text-to-speech | `gpt-4o-mini-tts` | Per-language accent, voice gender and speed. Browser speech synthesis as offline fallback |
| Spoken numbers | Deterministic Python (`numerals.py`) | Oshiwambo and Otjiherero numerals are built in code, not generated. See below |
| Notebook OCR | `claude-sonnet-5` (vision) | The one place we pay for quality. Handwriting is hard and a scan happens rarely |

Cost control: compact tool results, history trimmed to 12 messages, capped output, static-first prompts so provider caching applies, weather cached 6 hours per location, and all proactive alerts computed by rules rather than the model.

---

## Speaking Oshiwambo and Otjiherero properly

No text-to-speech engine ships native voices for these languages, and the naive approach fails in a way a native speaker notices immediately: the model reads the sentence in Oshiwambo but says "fifty-three" and "fifteen hundred dollars" in English.

Asking an LLM to write the numerals doesn't work either. We tried it. `gpt-4o-mini` invented Oshiwambo words and collapsed into a repetition loop on Otjiherero.

Both languages build numbers regularly, so `numerals.py` implements the number systems directly:

```
53   ng: omilongo ntano na yatatu      kj: omirongo vitano na ndatu
1500 ng: eyuvi na omathele yatano      kj: eyovi na omasere ndano
```

Before anything is spoken, a deterministic pass rewrites digits, money, dates, percentages and units into native words, then the voice model is told exactly which language and accent it is reading. Every word the farmer hears is in their language. The number tables sit at the top of `numerals.py` for a native speaker to correct.

---

## Honesty

The agent is built to say what it doesn't know:

- Monitoring sites are **samples near** a farm, not measurements *of* that farm. The tools say so, and the prompt requires the agent to repeat it
- When the two weather APIs disagree, it reports the range and lowers its stated confidence
- Percentage rainfall anomalies are suppressed during the dry season, when the long-term normal is near zero and "+97% above normal" would describe a 3 mm shower
- Grazing-day estimates beyond a season are reported as "more than a full season" rather than a fake-precise day count
- No veterinary diagnosis, financial or legal advice, animal-health emergencies are pointed at the state vet

---

## Repo layout

```
main.py               FastAPI app, agent loop, endpoints
llm.py                Dual-provider router with failover
tools.py              The nine agent tools + region lookup
db.py                 SQLite schema and queries
insights.py           Proactive rules engine
protocols.py          Namibian vaccination protocols
prepare_real_data.py  Field-form → data/real_sites.csv
seed_demo.py          Demo farm
test_flow.py          End-to-end API test
static/               PWA: index.html, app.js, i18n.js, styles.css, sw.js
archive/              Real Lacuna Fund field dataset
```

## Testing

```bash
python test_flow.py     # signup → onboarding → register → calendar → insights → 5 agent questions
```
