# VeldWys — UI design brief

Paste everything below the line into Google Stitch. It is written as one prompt.

Context for you, not for Stitch: the app currently looks like a competent default —
soft beige gradient, white glass cards, emoji icons, rounded everything. Nothing is
wrong with it and nothing is *it*. This brief describes what the product is and what
it must survive, then hands over the look entirely.

---

## Design a mobile app called VeldWys

**VeldWys is a farm command centre for Namibian livestock farmers.** Not a chatbot with
a farm theme — a working register of real animals, with an AI advisor sitting on top of
it. Design it so the animals feel present and the AI feels like staff.

### Who is holding the phone

A Namibian farmer — communal or commercial — somewhere between Ondangwa and Gobabis.
Could be 28, could be 61. Mid-range Android, cracked screen protector, one bar of
signal, often no signal at all. Standing in a kraal in hard overhead sun, or in a bakkie,
or at a kitchen table at 5am before the animals go out. Sometimes wearing work gloves.
Their livestock is their bank account, their savings, and their inheritance, and they
have been keeping records of it in a hardcover notebook for twenty years.

They are not impressed by software. They will be impressed by something that respects
what they already know.

### The one idea the design must carry

**The register is the heart, not the chat.** Every screen should make it obvious that
this app knows their actual animals — ear tag TE-TANGA S009, the brown ewe with the
white spot on her tail, vaccinated in March. The farmer must never have to re-explain
their herd size or where their farm is. The AI is valuable *because* it already knows;
design should show that knowing, not hide it behind a text box.

### Screens to design

**Getting in**
1. **Sign in / sign up** — one form, toggles between the two.
2. **Forgot password** — username, then a security question they chose, then a new password.
3. **Onboarding, 5 steps** — language · farm name and location on a map · grazing area
   and rough animal counts · offer to set up the standard Namibian vaccination
   schedule · done. Make this a journey that shows them what they are about to get,
   not a form queue. This is where they decide whether the app is for them.

**The daily app** (five-tab bottom navigation)
4. **Dashboard** — a green/amber/red state of the farm, proactive insights (overgrazing,
   drought, overdue vaccinations), upcoming tasks, quick actions.
5. **Herd** — the list of individual animals. Ear tag, species, sex, colour and
   markings, status. Filterable, searchable, and it may hold several hundred rows.
6. **Animal detail** — one animal, its full history: vaccinations, treatments, births,
   weights, sale.
7. **Analytics** — stocking rate vs. regional carrying capacity, herd composition,
   births/sales/deaths over time, rainfall, pasture condition.
8. **Chat** — asking the advisor questions, in any of five languages. Answers carry a
   green/amber/red verdict badge and an expandable "how I worked this out" trace.
9. **Settings** — profile, farm location, language, voice (gender, speed), documents.

**The moments that matter most**
10. **Voice conversation — full screen.** The farmer is talking hands-free while
    working. There is a listening state, a transcribing state, a thinking state, and a
    speaking state, and the screen must make which one is happening obvious from two
    metres away in sunlight. Something alive at the centre that reacts to their actual
    voice while listening and to the reply while speaking. A live caption. A large,
    unmissable way to end it. This screen is the emotional high point of the product —
    give it your best work.
11. **Notebook scan** — photograph pages of a paper stock book, several at once. Then a
    **review screen**: every extracted animal as an editable record, with uncertain ones
    flagged and floated to the top, duplicate ear tags warned about, and a plain-language
    summary of how the page was read. This is the feature that converts twenty years of
    paper into the register, and the review step is where trust is won or lost.
12. **Offline state** — a calm, non-alarming indication that this is saved data and
    anything logged now will sync later. Offline is normal here, not an error.
13. **Language picker** — five languages, chosen often, sometimes by someone else
    borrowing the phone.

### Hard constraints — please treat these as non-negotiable

- **Mobile-first PWA**, installed to the home screen. Must handle iPhone notch and
  Android punch-hole safe areas top and bottom, portrait and landscape.
- **Five languages: English, Afrikaans, Oshindonga, Oshikwanyama, Otjiherero.** The
  Bantu languages run roughly 2–2.5× the width of English and compound heavily. Real
  strings you must design to survive:
  - "Listening…" → **"Otandi pulakene…"**
  - "Transcribing" → **"Otandi uvu ko ondaka yoye…"**
  - "Carrying capacity" → **"Omuvalu tagu vulika"**
  - "Large stock units" → **"oiyuunga yoimuna"**
  No fixed-width buttons, no labels that must stay on one line, no truncation of
  anything meaningful. Test your layouts against the longest string, not the English.
- **Outdoor legibility.** Hard sun, mid-range screen. Generous contrast and type size.
  Nothing critical in thin light-grey text.
- **Gloved-hand touch targets.** Minimum 48dp, generous spacing on anything destructive.
- **The green/amber/red verdict system must never rely on colour alone** — pair it with
  shape, icon, and text. Colour-blindness and glare both defeat colour-only signals.
- **Works offline.** Nothing in the design may assume a spinner will resolve.
- **No custom icon font or remote asset dependency** — the app ships as a self-contained
  PWA with no build step.

### Tone

Namibian rangeland. Earned, practical, quietly confident — a good tool, well kept. The
feeling of a well-made leather-bound stock book and a solid bakkie, not a startup
dashboard and not a tourist safari brochure. It should look like it was made *for* this
place by someone who has been there, rather than themed after it from far away.

Take that as a direction, not a specification.

### Please avoid

- Generic AI-SaaS looks: purple-blue gradients, glassmorphism as the default surface,
  floating 3D blobs.
- **Emoji as the icon system.** The current build does this and it is the single
  cheapest-looking thing about it.
- Cards inside cards inside cards.
- Safari clip-art: acacia silhouettes, sunset gradients, tribal-pattern borders. The
  audience is the farmer, not a visitor.
- Dense desktop-style data tables squeezed onto a phone.

### What I would like back

**Two or three genuinely different directions**, not three tints of one idea — different
enough that choosing between them is a real decision. For each: the colour system, type
scale, iconography approach, and the core surface/card treatment, applied to at least
the dashboard, the herd list, the voice conversation screen and one onboarding step.

Beyond the constraints above, the palette, typography, layout, motion, iconography,
illustration and overall personality are yours. Push it further than you think I want.
The constraints are about the farmer's hands and eyes and languages; everything else is
open, and I would rather see something with a point of view than something safe.
