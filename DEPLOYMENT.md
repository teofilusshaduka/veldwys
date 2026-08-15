# VeldWys — deployment roadmap

Written after the hackathon win, 2026-08-06. This is what stands between the current
build and real farmers using it.

**The framing that should drive every decision below:** VeldWys is not a chatbot. It is
a farmer's **asset register** — the digital record of their savings, their pension and
their inheritance. Losing that data, or leaking it, is a materially worse outcome than
the app being down. Availability is a convenience; integrity and confidentiality are
not.

---

## Phase 0 — Do not deploy without these

Four items. Everything else on this page can slip; these cannot.

### 0.1 Authentication — the single biggest blocker
**Status: completely absent.** Every endpoint takes `user_id` as a query parameter and
trusts it. `GET /api/animals?user_id=3` returns farmer #3's entire herd to anyone who
asks. There are **27** such endpoints.

- [ ] Add a `sessions` table (token, user_id, created_at, expires_at, revoked) — simpler
      and more revocable than JWT at this scale
- [ ] Issue a token on login; return it instead of the bare `user_id`
- [ ] FastAPI `Depends(current_user)` dependency that resolves the token to a user
- [ ] **Replace `user_id: int` with the authenticated user on all 27 endpoints.** Do
      this mechanically and check every one — a single missed endpoint reopens the hole
- [ ] Frontend: store the token, send `Authorization: Bearer`, handle 401 by logging out
- [ ] Write a test that asserts farmer A cannot read farmer B's animals

*Effort: 1–2 days. Nothing ships before this.*

### 0.2 Spend protection
`/api/scan_notebook` costs **$0.056 per call** and is currently open to the internet.
A script could run up hundreds of dollars overnight.

- [ ] Auth (0.1) closes the anonymous path — necessary but not sufficient
- [ ] Per-user daily quotas: scans/day, chat messages/day, TTS characters/day
- [ ] Hard monthly spend cap with an alert at 50% and a kill switch at 100%
- [ ] Billing alerts on both the OpenAI and Anthropic consoles
- [ ] Return a friendly "you've reached today's limit" rather than a 500

*Effort: half a day.*

### 0.3 Backups
The register lives in a single 160 KB SQLite file with **no backup of any kind**. One
bad disk and 275 animals across 8 farms are gone permanently.

- [ ] Enable SQLite **WAL mode** — also fixes concurrent-write "database is locked"
      errors that will appear the moment two farmers use it at once
- [ ] **Litestream** streaming replication to object storage (S3/Backblaze). Continuous,
      cheap, and the right tool for SQLite at this scale
- [ ] Nightly snapshot with 30-day retention, stored in a different region
- [ ] **Practise a restore.** A backup you have never restored is a hope, not a backup
- [ ] Farmer-facing CSV export (already exists — verify it covers everything)

*Effort: half a day. Do this before the pilot, not after.*

### 0.4 Secrets
- [ ] `.env` is correctly gitignored — **verify the keys were never committed**:
      `git log -p --all -S 'sk-' | head` — if they were, rotate immediately
- [ ] Move keys to the host's secret store, never a file on the box
- [ ] Rotate both API keys before going live (they've been on a laptop shared with a
      hackathon demo)

*Effort: 1 hour.*

---

## Phase 1 — Minimum viable deployment

### 1.1 Hosting — pick a region close to Namibia
Latency matters: the voice loop is listen → transcribe → think → speak, and every
round trip crosses it. Europe/US hosting adds 150–300 ms per hop.

| Option | Region | Notes |
|---|---|---|
| **Fly.io** | Johannesburg (`jnb`) | **Recommended.** Closest to Namibia, SQLite+Litestream friendly, cheap, simple |
| AWS | `af-south-1` Cape Town | More control, more work, more cost |
| Railway / Render | EU/US only | Simplest, but the latency shows up in voice |

- [ ] Choose host (recommend Fly.io `jnb`)
- [ ] Write a `Dockerfile` — none exists yet
- [ ] Pin dependency versions; current `requirements.txt` uses `>=` throughout, so a
      breaking upstream release can take production down without a code change
- [ ] Health check endpoint for the platform to poll

### 1.2 Domain, TLS, PWA
- [ ] Register a domain (`veldwys.na` if obtainable, else `.com`)
- [ ] TLS — mandatory, not optional: microphone access and PWA install both require HTTPS
- [ ] Update `manifest.json` and the service worker scope to the real origin
- [ ] Retire the Tailscale URL

### 1.3 Data layer
- [ ] WAL mode (see 0.3)
- [ ] Decide SQLite vs Postgres. **Recommendation: stay on SQLite + Litestream** through
      the pilot. It is genuinely sufficient to a few hundred farmers, and it keeps the
      offline-first story simple. Revisit at ~500 concurrent users
- [ ] Add indexes on `animals(user_id)`, `animal_events(user_id)`, `chat_history(user_id, chat_id)`
- [ ] Move `data/uploads` to object storage — container filesystems are ephemeral

### 1.4 Observability
You currently learn about failures when a farmer tells you. The TTS 500 ran in
production for hours before anyone noticed.

- [ ] Sentry (or equivalent) for exceptions, with alerts
- [ ] Uptime monitor hitting the health check
- [ ] Structured logging with request IDs
- [ ] A dashboard for per-day API spend

### 1.5 Release process
- [ ] Git branch → CI → deploy. No more editing files on a laptop that serves traffic
- [ ] GitHub Actions running `test_flow.py` and `test_scan_eval.py` on every PR
- [ ] **Automate the service worker cache bump** — it is manual today and has already
      caused a silent stale-asset bug twice
- [ ] Staging environment that mirrors production

---

## Phase 2 — Before real farmers touch it

### 2.1 Legal and privacy
Non-negotiable once you hold other people's asset data.

- [ ] Privacy policy and terms — in **all five languages**, not just English
- [ ] Namibia's Data Protection Bill is progressing; POPIA applies if you hold South
      African users' data. Get someone who knows Namibian law to read it
- [ ] Explicit consent at signup for storing herd data and sending it to AI providers
- [ ] Data retention and deletion policy — a farmer must be able to leave with their data
- [ ] Confirm your position on OpenAI/Anthropic data handling, and state it plainly to
      farmers. "Where does my herd data go" is a fair question and you should have a
      crisp answer

### 2.2 Product gaps
- [ ] **Protocol strings are untranslated** — vaccination reminders render in English
      inside Oshiwambo and Afrikaans screens. Visible on the dashboard today
- [ ] Native-speaker review pass using `/review` for Oshindonga and Oshikwanyama
- [ ] Oshiwambo ASR is weak — set expectations in the UI rather than letting it fail silently
- [ ] Voice orb was squared off in the redesign; it reads as a static block
- [ ] Account deletion in-app
- [ ] A support channel a farmer can actually reach (WhatsApp is realistic here)

### 2.3 Pilot
- [ ] 5–10 farmers, recruited deliberately, ideally across regions and languages
- [ ] Onboard them in person — watch where they get stuck, don't rely on reports
- [ ] Instrument: scans attempted vs confirmed, questions asked, retention
- [ ] Weekly check-ins for a month
- [ ] **Set an explicit kill criterion** — what result means you stop or pivot

---

## Phase 3 — Scale

- [ ] Postgres migration when SQLite write contention shows up
- [ ] Per-farmer cost dashboard (unit economics are your strongest asset — protect them)
- [ ] Offline write queue with conflict resolution
- [ ] SMS gateway for password recovery (the security question is a stopgap)
- [ ] Oshiwambo speech dataset collection — the ASR gap is a data problem, not a model
      problem, and it is a genuine moat for a Namibian team
- [ ] Extension officer / co-op accounts (one advisor, many farms)
- [ ] Ministry of Agriculture or Meatco partnership for distribution

---

## Suggested order

| Week | Focus |
|---|---|
| 1 | 0.1 auth · 0.4 secrets rotation |
| 2 | 0.2 quotas · 0.3 backups + WAL · Dockerfile |
| 3 | Deploy to Fly.io `jnb` · domain + TLS · Sentry · CI |
| 4 | Legal copy · protocol translations · native-speaker review |
| 5–8 | Pilot with 5–10 farmers |
| 9+ | Iterate on what the pilot actually shows |

**Fastest honest path to a real deployment: about three weeks**, assuming auth is done
properly rather than quickly.

---

## The one thing not to compromise

Auth. It is tempting after a win to put the demo online so people can try it, and the
demo has no access control at all. Anyone could enumerate `user_id=1,2,3` and read every
farm on the system, or write to it.

If you need something public before auth is done, deploy a **separate seeded demo
instance** with fake farms and no real data, and keep the real one closed. Do not put
live farmer records behind an integer.
