# VeldWys — Session Handoff

DLIX Namibia 2026 Hackathon submission. Written 2026-07-31, ~08:00, right after
pushing to GitHub with the 10:00 deadline close behind.

## Where things stand right now

- **Pushed to GitHub**: https://github.com/wytee64/indaba-hackathon-project
  (`main`, commit `6eb13c8`). Repo is currently **private** — confirm with Teo
  whether it got flipped public or judges were added as collaborators before
  trusting that the link is reachable by anyone else.
- **Server**: FastAPI + uvicorn, was last run via
  `nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --reload`,
  logging to `/tmp/veldwys.log`. Check if it's still alive before assuming so.
- **Phone demo**: served over `tailscale serve` at
  `https://teofiluss-macbook-pro.taile383b5.ts.net/`. HTTPS is required there
  for mic access (`getUserMedia`) and PWA install — plain `http://100.x.x.x`
  will not work for those two things.
- **Service worker cache**: bumped to `veldwys-v7` in `static/sw.js`. If future
  frontend edits don't show up on a device, bump this string again — that's
  almost always the cause, not a server problem.

## What the app actually is

The differentiator from a plain grazing chatbot: the LLM agent is a thin layer
over a **livestock register** (individual animals, ear tags, vaccination
history) plus real farm context (location, camp area, language), so the
farmer never has to restate their herd size or where their farm is. That
context gets injected into every chat call — see `main.py`'s per-request
"FARMER CONTEXT" system message, built from `db.get_herd_summary`,
`db.get_upcoming_events`, and the profile row.

Core stack:
- **Backend**: `main.py` (FastAPI app, all endpoints), `db.py` (SQLite,
  schema + queries), `tools.py` (9 async agent tools + dispatch), `llm.py`
  (OpenAI/Anthropic dual-provider router with failover)
- **Domain logic**: `protocols.py` (static Namibian vaccination schedules →
  dated reminders, zero LLM cost), `insights.py` (proactive rule engine, zero
  LLM cost), `analytics.py` (herd/grazing/rainfall analytics), `numerals.py`
  (native-language number/currency words for TTS)
- **Data**: `data/rangeland.csv` (synthetic, from `generate_synthetic_data.py`),
  `data/real_sites.csv` + `data/real_grazing.csv` (real Lacuna Fund / UNAM /
  Farm4Trade field data, parsed by `prepare_real_data.py` from
  `archive/fieldform_*`)
- **Frontend**: `static/` — vanilla JS, no build step. `app.js`, `i18n.js`
  (en/af/ng/kj), `index.html`, `styles.css`, `sw.js` + `manifest.json` for PWA
- **Voice**: `/api/transcribe` (whisper-1 + gpt-4o-mini correction pass),
  `/api/tts` (gpt-4o-mini-tts with a speech-prep pass for native-language
  numbers/currency, per-language accent instructions, gender + speed options)

Model choices (the cheap-but-not-compromised strategy): `gpt-4o-mini` for
chat and transcript correction, `whisper-1` for ASR, `gpt-4o-mini-tts` for
voice, `claude-sonnet-5` reserved for vision-only work (notebook OCR /
document photo ingestion). `claude-haiku-4-5` is the Anthropic-side failover
for chat if OpenAI errors.

## What's built (all of round 1 + round 2 feedback)

Everything through task #16 in the TaskCreate list is done: livestock
register + LSU math, real dataset integration, multilingual onboarding,
vaccination protocols, voice + TTS + morning briefing, insights engine,
notebook vision scan, offline PWA, seed data, the 8 phone-test bug fixes,
voice overhaul + conversation mode (RMS voice-activity detection, hand-rolled
since `@ricky0123/vad-web` conflicts with the offline-first build), chat
writes to the herd (`update_animals`, `complete_task`, daily debrief), chat
management + doc upload + retranslate-on-language-switch, humanized copy +
grounded market prices (`get_market_prices` tool, always cited as
indicative), analytics tab, and settings/profile depth.

The full plan with all the detail lives in
`/Users/teofilusshaduka/.claude/plans/users-teofilusshaduka-library-container-distributed-thunder.md`
if you need the reasoning behind any of the above.

## What's still open (task #17, in progress)

This was the last thing being worked on before the GitHub push took priority:

- **Oshiwambo TTS spot-check**: Teo needs to listen to Oshiwambo (and ideally
  Otjiherero) voice samples as a native speaker and confirm the numbers/
  currency sound right. Any correction he gives should be pinned as a literal
  override in the speech-prep prompt or a small dict, not just fixed once and
  forgotten.
- **Full E2E pass** per the plan's verification section:
  - `test_flow.py` coverage for: "I sold 3 goats" flips 3 goat records to
    `sold`; `complete_task` closes a reminder by fuzzy match; chat CRUD +
    search; doc upload with the agent citing it; `/api/translate_chat`; TTS
    with `{lang:'ng', gender:'male'}` returns audio
  - Mobile-viewport browser check: verdict pill shows its label once (not
    twice — this was bug #1 from phone testing); Listen button toggles
    cleanly and never overlaps; protocol reminders render in Oshiwambo, not
    English; analytics tab renders offline
  - Phone-over-Tailscale check: notch is clean in both Safari and the
    installed PWA (bug #3, fixed via `black-translucent` status bar style —
    confirm it actually looks right on the device); conversation mode
    completes a full listen→transcribe→reply→speak→listen loop without
    manual taps

## Known constraints / things not to re-litigate

- Teo handles GitHub himself — I do the code, he owns push/PR/repo settings
  normally. (This session was an exception: he explicitly asked me to push
  because of the deadline crunch.)
- Local demo only, no cloud deployment — Tailscale is the whole mobile story.
- Offline-first is a hard requirement (connectivity is a real barrier for
  Namibian farms), not a nice-to-have — don't suggest cutting the service
  worker / offline queue to save time.
- Cost discipline matters: don't casually upgrade model choices (e.g. don't
  swap `gpt-4o-mini` for `gpt-4o` in chat) without a specific quality reason,
  per Teo's "cheap but don't compromise quality" brief.

## If the deadline has already passed when this is read

Don't restart feature work reflexively — check with Teo first on whether the
submission is locked (hackathon judging may already be running against the
pushed commit) before making further changes to `main`.
