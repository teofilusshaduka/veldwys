# VeldWys — presentation content

Slide content and talking points for a 15-minute slot. Build the slides yourself; this
is what goes on them and what to say. The "Say" sections are written as full paragraphs
you can read or paraphrase out loud — not fragments to reconstruct on stage.

Every cost figure here was **measured**, not estimated — the method is at the bottom so
you can defend any number a judge questions.

---

## The 15-minute shape

| # | Slide | Time | Cut priority |
|---|---|---|---|
| 1 | The farmer and the notebook | 1:30 | Never cut |
| 2 | The insight: register first, chatbot second | 1:30 | Never cut |
| 3 | **DEMO — notebook scan** | 3:00 | Never cut |
| 4 | **DEMO — voice, in Oshiwambo** | 2:00 | Never cut |
| 5 | Getting the language right | 2:00 | Shorten to 1:00 |
| 6 | What it costs to run | 2:00 | Never cut |
| 7 | How we know it works (the eval) | 1:30 | Cut to a single line on slide 3 |
| 8 | What's real vs what's next | 1:00 | Shorten |
| 9 | Close | 0:30 | Never cut |

Running behind? Drop slide 7 first, then compress 5. Never cut 3, 4, or 6 — those are
the three things a judge remembers.

---

## Slide 1 — The farmer and the notebook

**On the slide:** one photo of the real handwritten stock book. Ear tags, colours,
`Ewe` / `Ram` / `Kapater`. No bullet points competing with it.

**Say:**

Livestock is the backbone of the rural Namibian economy, and for most farmers the herd
isn't just an asset — it's the savings account, the pension, and the inheritance, all
at once. What you're looking at is a real page from a real farmer's notebook. Twenty
years of records like this exist across the country: the entire asset register of a
farm, written in pen, kept in one notebook, in one place, with no backup anywhere.

Every piece of digital farming software offered to this farmer so far has assumed he'd
sit down and retype all of it. He won't do that, and honestly, he shouldn't have to.

We didn't start by asking what AI could do for farmers. We started with the notebook.

---

## Slide 2 — Register first, chatbot second

**On the slide:** two boxes. *Generic farming chatbot* → "How many cattle do you have?
Where is your farm? What breed?" every single time. *VeldWys* → knows TE-TANGA S009 is
a brown ewe with a white spot on her tail, vaccinated in March.

**Say:**

Anyone can put a grazing prompt in front of a language model and call it a farming
assistant. That's a demo, not a product, because it forgets the farm the moment you
close the tab. VeldWys is built the other way around: it's a livestock register first,
with an advisor sitting on top of it. Every question the farmer asks carries the real
context of that farm automatically — herd composition, ear tags, camp size, region,
rainfall, vaccination history. The farmer never has to restate any of it. That's the
entire design philosophy in one sentence.

And it isn't read-only. The advisor has nine tools it can actually use, including
writing back to the register — so if a farmer says "I sold three goats," three animal
records actually flip to sold, right there in the conversation.

The AI is the thin part. The register is the product.

---

## Slide 3 — DEMO: the notebook scan *(flagship — most time)*

**On the slide:** the notebook photo on the left, extracted editable records on the
right, with a `Kapater` row and an untagged row visibly flagged.

**Do live:** photograph a page, watch it come back as records, correct one field, save.
Then show the *pile* of pages going in at once.

**Say:**

This is the feature that decides whether the app actually gets used or not. If
onboarding means manual typing, nobody onboards — full stop. So we built a scan that
turns a photograph of a handwritten page directly into editable records.

The important part is that it isn't tuned to my notebook specifically. The pipeline
reads the page on its own terms first — is this even a table, what does each column
seem to hold, are there section headers grouping the rows — and only after that does it
map what it found onto our schema. That means it copes with column order changing,
headers being missing entirely, free-text lists, a vaccination diary, even a tally
sheet, because it isn't pattern-matching against one layout.

It also handles the messy reality of a real notebook: ear tags written across two
lines, rows with no tag at all, rows that have been struck through and must not be
imported, duplicate tags, even a phone number scribbled in the margin that shouldn't
end up in a field. And "Kapater" — a castrated male — had no home at all in a simple
male-or-female schema. Real registers need that distinction, so now ours has it.

Nothing gets saved until the farmer confirms it on screen. Uncertain records float to
the top, and the app tells you plainly how it read the page, so the farmer is always in
control of what lands in their register.

**If a judge asks "did you train a model?":** No, and we didn't need to. The gain came
from splitting the job into two steps and never showing the model the target format
until the second one.

---

## Slide 4 — DEMO: voice, in the farmer's language

**On the slide:** the full-screen voice view, orb mid-pulse.

**Do live:** ask it something in Afrikaans or Oshiwambo, hands off the phone.

**Say:**

Text input quietly assumes two things: that you're comfortable reading and typing, and
that you can do it in your own language. Neither is a safe assumption here, and neither
is realistic for a farmer standing in a kraal with gloves on. So VeldWys has a full,
hands-free conversation mode. It listens, hears when you've paused, answers out loud,
and starts listening again — no tapping the screen at any point.

It also adapts to the room it's in. At the start of every turn it quietly samples the
background noise and sets its listening threshold from that, so the same app works in a
quiet kitchen and next to a running bakkie without being retuned. And it knows not to
transcribe its own spoken reply back as the next question.

All of this works end to end in five languages — the question, the answer, and the
spoken reply.

**The honest bit, say it before a judge finds it:** Oshiwambo speech recognition
specifically is still weak, because the underlying model has almost no training data
for it. We fixed what was fixable — it no longer silently answers in English when it
mishears — and we're upfront about what isn't fixed yet. Oshiwambo as written text, and
Oshiwambo spoken back to the farmer, are both solid.

---

## Slide 5 — Getting the language right

**On the slide:** a before/after table of three real errors. This slide earns more
credibility than any feature slide.

| Was | Literally means | Now |
|---|---|---|
| `omugongo gwoshimeni` | "the **spine** of anthrax" | `ondjeka yaanthrax` — anthrax injection |
| `dhi na omakutsi` | "they **have ears**" (for *ear-tagged*) | `dhi na iidhindilo` |
| `iikadhona` | "**girls**" (used for cows) | `oonkadhi` |
| `Omulumentu` / `Omukiintu` | a **human man / woman** (for animal sex) | `Ondume` / `Onkadhi` |

**Say:**

We shipped with four languages in our first round. Then a native Oshiwambo speaker
opened the app and told us it simply didn't read like Oshiwambo. He was right, and it
wasn't a polish problem — it was three real faults at once. The file mixed two
different orthographies in the same document, the grammar around noun classes was
broken throughout, and in several places we had, honestly, just the wrong word.

Once we fixed that, we split the languages up properly. Oshindonga and Oshikwanyama had
been collapsed into a single language when they're not the same, and Otjiherero was
sitting on Oshikwanyama's own ISO code. Today we have five languages, 286 strings each,
with full parity across all of them.

We also built a review tool so a native speaker can correct the file directly, rather
than reporting a bug to a developer who then has to guess again at the right word.

Anyone can run text through a translation API. Knowing that it says "the spine of
anthrax" instead of "anthrax injection" takes an actual speaker in the room. We built
the workflow that keeps one there.

---

## Slide 6 — What it costs to run *(the slide judges remember)*

**On the slide:** the measured table. Big type on **N$2 per farmer per month**.

### Measured cost per operation

| Operation | Measured usage | Cost (USD) |
|---|---|---|
| Chat question (agent + tools + farm context) | 2,762–6,975 in / 70–116 out | **$0.00064** |
| Voice question (Whisper + correction pass) | ~6s audio | **$0.00068** |
| Spoken answer (TTS) | 173 characters | **$0.0021** |
| **Full voice turn** (ask → answer → spoken) | | **$0.0034** |
| Notebook page scan (2-pass, Opus 5 + Sonnet 5) | 5,271 in / 1,680 out | **$0.056** |

### What that means per farmer

| | USD | N$ |
|---|---|---|
| Per month (60 text questions + 20 voice turns) | **$0.11** | **N$2.00** |
| One-time: digitising a 20-page notebook | **$1.12** | N$21 |
| **Year one, all in** | **$2.40** | **N$44** |
| 1,000 farmers, year one | **$2,404** | N$44,000 |

**Say:**

A full year of AI advice for one farmer costs less than a single cup of coffee.
Digitising twenty years of paper records costs about N$21, and that's a one-time cost,
not a recurring one.

I want to be clear that this isn't an estimate we made up to sound good. We
instrumented the running application and read the actual token counts off real
requests — the method is documented at the end of this deck if anyone wants to check
our working.

We got these numbers by being deliberate about where the money actually goes. Two
things in this app cost real money: reading handwriting, and reasoning through a
question, so those are the only places we spend on strong models. The vaccination
schedules and the proactive insight rules are plain Python with zero LLM cost, because
a calendar simply doesn't need a language model to run it. And the one genuinely
expensive operation — scanning a notebook — is something that happens once per farmer,
ever. The thing that happens every single day costs about six hundredths of a US cent.

At N$2 a month, this scales to every communal farmer in Namibia, and the AI bill is not
what's going to stop us.

---

## Slide 7 — How we know it works

**On the slide:** `89/89 checks passed across 6 page formats`.

**Say:**

We didn't just eyeball the scan and call it done — we graded it against notebook pages
laid out six genuinely different ways: no header row at all, columns in a different
order, a free-text list instead of a table, a date-led diary, a tally sheet, and an
Afrikaans-labelled form.

The two hardest cases in that set are the ones that matter most. A tally sheet that
just says "cattle 47, goats 112" has to produce two counts, not 226 invented animal
records. And a row that's been struck through on the page has to be recognised as
deleted and left out entirely. It passes both of those, along with everything else —
eighty-nine out of eighty-nine checks.

We also deliberately checked that our own test suite is capable of failing, because a
green suite that can never turn red doesn't actually prove anything.

So when we say it works on notebooks it has never seen before, that isn't a hope — it's
something we specifically measured.

---

## Slide 8 — What's real, and what's next

**On the slide:** two honest columns.

**Working today:** livestock register with individual animals · notebook scan · 5
languages · voice conversation · offline-first PWA (works with no signal) · Namibian
vaccination schedules · proactive insight engine · real rangeland data (Lacuna Fund /
UNAM / Farm4Trade) · analytics · password recovery.

**Known gaps, said out loud:** Oshiwambo speech recognition is weak (no training data
exists) · TTS accents need native-speaker tuning · API endpoints have no auth yet —
fine for a demo, first thing to fix · no SMS, so password recovery uses a security
question.

**Say:**

We'd rather name our own weak spots than have a judge find them first. Every one of
these gaps is going to be visible to someone in this room eventually, so we're putting
them on the slide ourselves — being first with that is worth more to us than being
lucky. And to be clear, none of these gaps are architectural problems. They're all
scoped, understood, and on the list.

---

## Slide 9 — Close

**Say:**

Namibian farmers have been keeping excellent records for decades. They never needed to
be taught how to collect data — what they needed was a piece of software willing to
meet them where that data already lives, which is a paper notebook, not a form.

VeldWys reads that notebook, speaks the farmer's own language, works with no signal at
all, and costs about N$2 per farmer per month to run.

The notebook was never the problem. Nobody had bothered to read it.

---

## Feature ranking — cut from the bottom

Ranked by *demo impact and defensibility*, not by how hard they were to build.

| # | Feature | Why it ranks here |
|---|---|---|
| 1 | **Notebook scan / bulk onboarding** | Solves the actual adoption blocker. Visually striking. Format-agnostic and we can prove it. |
| 2 | **The register as foundation** | The whole differentiator. Without this it's a chatbot with a farm theme. |
| 3 | **Cost** | N$2/farmer/month, measured. Turns "nice demo" into "this could actually deploy." |
| 4 | **Five languages, done properly** | Two Oshiwambo variants + the review workflow. Nobody else will have gone this deep. |
| 5 | **Voice conversation mode** | Great live. Adaptive noise handling is a real differentiator. Weakened by Oshiwambo ASR — demo in Afrikaans or English. |
| 6 | **Offline-first PWA** | Deeply relevant to rural Namibia; hard to *show* in a room with wifi. Mention, don't demo. |
| 7 | **Proactive insights** | Tells the farmer things unprompted. Bonus: zero LLM cost — supports the cost story. |
| 8 | **Namibian vaccination protocols** | Real domain grounding, real dated reminders. Also zero LLM cost. |
| 9 | **Real field data** | Lacuna Fund / UNAM / Farm4Trade. One credibility line, not a slide. |
| 10 | **Analytics** | Good screenshot, weak story. Every app has charts. |
| 11 | **GPS + offline place search** | Good UX thinking. One sentence inside the onboarding demo. |
| 12 | **Password recovery** | Necessary, not interesting. Only if asked. |
| 13 | **Document upload, chat management** | Cut. |

**5-minute version:** slides 1, 3, 6, 9.
**10-minute version:** add 2 and 4.

---

## Questions you should expect

**"Isn't this just ChatGPT with a farming prompt?"**

No, and here's the easiest way to show the difference. Ask ChatGPT how much grazing you
have left, and it will ask you five questions before it can even try to answer. Ask
VeldWys the same thing, and it just answers, because it already knows your herd, your
hectares, your region, and your rainfall. It's not a one-way conversation either — it
writes back, so telling it you sold three goats actually updates three records in the
register.

**"What happens with no signal?"**

VeldWys is built offline-first as a progressive web app. The register, the analytics,
and the reminders all open with no connection at all. Anything the farmer logs while
offline simply syncs the moment signal comes back.

**"How do you know the OCR is accurate?"**

We grade it against six genuinely different notebook formats, and it passes all
eighty-nine checks across them. And beyond the automated testing, nothing ever reaches
the actual register until the farmer has looked at it and confirmed it on screen.

**"Can you afford to run this at scale?"**

N$2 per farmer per month, and that's a measured number, not an estimate. A thousand
farmers costs roughly N$44,000 in the first year, and most of that is the one-time cost
of digitising each farmer's notebook, not the ongoing running cost.

**"Who validated the translations?"**

A native Oshiwambo speaker on our own team, which is exactly how we caught the app
telling people it was giving them "the spine of anthrax." We built a review tool
specifically so that check keeps happening as the app grows, not just once.

**"What would you do with more time?"**

Proper authentication on the API, an SMS gateway for password recovery, and collecting
real Oshiwambo speech data. That last one is a dataset problem, not a model problem —
and it's exactly the kind of gap a Namibian team is best placed to close.

---

## Appendix — how the cost numbers were produced

Say this if challenged; it's the difference between a claim and a measurement.

Every figure comes from instrumenting the running application and reading the actual
usage token counts off real API responses, not from a pricing calculator or a rough
guess. The chat cost is averaged over four real farm questions asked against a seeded
herd, including turns where the agent calls tools and makes two API round trips instead
of one. The scan cost is measured on a real fixture page, with both passes and their
input and output tokens counted separately.

The published prices we used, per million tokens, are: Opus 5 at $5 input and $25
output, Sonnet 5 at $3 and $15, GPT-4o-mini at $0.15 and $0.60, and Whisper at $0.006
per minute of audio. Sonnet 5 is actually on introductory pricing right now at $2 and
$10, which would make the scan cost roughly 10% cheaper than what we're showing — we
used the full list price on purpose, so our number is the conservative one, not the
flattering one.

The monthly model assumes sixty text questions and twenty voice turns per farmer per
month; that assumption can be scaled however a judge prefers, since the real output
here is the per-operation cost, not the monthly multiplier. All rand figures use a
conversion rate of 18.5 N$ to the US dollar.
