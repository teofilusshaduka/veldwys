# VeldWys deck — Stitch prompts

**How to use this.** Stitch builds screens, not decks. Each slide is one 1920×1080
desktop screen; you export them and assemble the deck yourself (Figma, Slides, or
straight to HTML).

Paste **Prompt 0** first — it sets the design system and gets you the title slide. Then
paste each slide prompt in the same session so Stitch carries the visual language
forward. Don't paste all ten at once; Stitch degrades when a single prompt asks for
many screens.

If you're short on time, generate slides **1, 3, 6, 9** — that's the 5-minute deck.

---

## Prompt 0 — design system + title slide

> I'm designing a conference presentation as a series of 1920×1080 desktop screens.
> Each screen is one slide. Start by establishing a design system, then design the
> title slide.
>
> **The talk:** VeldWys — an AI advisor for Namibian livestock farmers, built around a
> digital livestock register. Presented at a hackathon in Namibia, 15 minutes, to
> judges who have already sat through a dozen AI demos today.
>
> **Viewing conditions that drive every decision:**
> - Projected in a lit room, viewed from up to 10 metres back. Body text no smaller
>   than 28px at 1920 wide; anything that matters, far larger.
> - Judges read the slide in about 3 seconds and then look back at the speaker. Every
>   slide needs exactly one thing that reads instantly.
> - Slides support a speaker — they are not a document. Never more than ~25 words of
>   body copy on a slide.
>
> **Tone:** Namibian rangeland — earned, practical, quietly confident. The feeling of a
> well-kept leather stock book and a solid bakkie. Serious enough that a room of judges
> takes the economics seriously, warm enough that it never feels like a corporate
> quarterly review. Not a startup pitch template, not a safari brochure.
>
> **Design system to establish and reuse across every slide:**
> - A colour palette rooted in Namibian rangeland, working under projector washout.
>   Strong contrast; no thin light-grey text on white.
> - A type scale with a display face for slide statements and a highly legible face for
>   data and tables. Numbers must be a feature, not an afterthought — this deck has a
>   slide that is almost entirely numbers.
> - A consistent slide skeleton: where the statement sits, where supporting detail
>   sits, where the slide number sits.
> - A treatment for the recurring element: a photograph of a handwritten notebook page.
>
> **Please avoid:** generic AI-pitch aesthetics — purple-blue gradients, glassmorphism,
> floating 3D shapes, stock photos of people pointing at laptops, clip-art acacia
> trees, sunset silhouettes, tribal-pattern borders. The audience is Namibian; visual
> shorthand aimed at foreign visitors will read as condescending.
>
> **Now design slide 1 — the title slide.**
> Content: the product name **VeldWys**. A one-line descriptor: *An AI advisor that
> reads the farmer's own notebook.* Space for a team name at the bottom.
> Make it confident and quiet. No tagline stack, no feature bullets.

---

## Slide 2 — the problem

> Next screen, same design system. This is the emotional open — the strongest image in
> the deck.
>
> A full-bleed photograph of a real handwritten livestock notebook page: ruled columns,
> ear tag numbers, colour descriptions, some rows crossed out. I will supply the photo
> — design the frame for it.
>
> Over it, one line only: **"Twenty years of records. One notebook. No backup."**
>
> No bullet points. No secondary text competing with the photograph. The photo is the
> argument; the speaker does the rest.

---

## Slide 3 — the insight

> Next screen. A two-sided comparison that resolves in favour of the right side.
>
> Left, labelled **"A farming chatbot"** — a chat bubble asking: *"How many cattle do
> you have? Where is your farm? What breed?"* Make it feel repetitive and tiring — this
> is the same interrogation every single session.
>
> Right, labelled **"VeldWys"** — showing that it already knows: ear tag `TE-TANGA
> S009`, brown ewe, white spot on tail, vaccinated March. Concrete, specific, settled.
>
> Underneath, one line across the full width: **"The AI is the thin part. The register
> is the product."**
>
> The left side should feel cluttered and the right side calm. That contrast is the
> whole slide.

---

## Slide 4 — the notebook scan (the flagship)

> Next screen. This is the most important slide in the deck — give it your best work.
>
> A transformation, left to right: the handwritten notebook page on the left becomes
> structured, editable livestock records on the right. Show the direction of travel
> clearly.
>
> On the right, show 4–5 record cards with real fields: ear tag, species, sex, colour
> and markings. Two of them carry small warning badges — one reading **"check this
> one"** and one reading **"no ear tag written."** Those flags matter: they show the
> farmer stays in control and nothing is saved unattended.
>
> A quiet caption along the bottom: **"Photograph the page. Check what it read. Save."**
>
> The handwriting side should feel human and imperfect; the records side clean but not
> sterile. Avoid making it look like a data-entry form.

---

## Slide 5 — voice

> Next screen. A phone shown at a comfortable angle, displaying a full-screen voice
> interface: a large glowing orb mid-pulse on a deep background, with a live caption
> beneath it reading a question in Afrikaans: *"Hoekom voel my beeste se koppe seer?"*
>
> Around or beside the phone, three short labels — no icons-with-paragraphs, just short
> phrases: **Five languages** · **Hands-free** · **Adapts to background noise**
>
> One line at the bottom: **"Speaks the language the farmer actually thinks in."**
>
> Keep it dark and focused so the orb carries the slide. This slide runs immediately
> after a live demo, so it should feel like a continuation of what they just watched.

---

## Slide 6 — the language work

> Next screen. A table slide, designed so the table itself is the visual — do not
> decorate around a plain table.
>
> Header: **"What our app was actually saying"**
>
> Three columns: *What it said* / *What it literally means* / *What it says now*
>
> | omugongo gwoshimeni | "the **spine** of anthrax" | ondjeka yaanthrax |
> | dhi na omakutsi | "they **have ears**" | dhi na iidhindilo |
> | iikadhona | "**girls**" — used for cows | oonkadhi |
>
> The middle column is the punchline — make it the column the eye lands on, and let the
> bolded words carry weight. The outer columns are supporting evidence.
>
> One line beneath: **"Five languages. 286 strings each. Checked by a native speaker."**
>
> This slide should feel like an honest confession that turns into a credential. Not
> apologetic, not boastful.

---

## Slide 7 — cost (the slide they remember)

> Next screen. The numbers slide. Everything here is measured data, so it should feel
> precise and unembellished — no infographic flourish, no gradients on the figures.
>
> One number dominates the screen, larger than anything else in the deck:
>
> **N$2** — with a smaller line beneath it: *per farmer, per month*
>
> Supporting figures, clearly secondary but legible from the back:
> - **N$21** — one-time, to digitise a 20-page notebook
> - **N$44** — per farmer, year one, everything included
> - **$0.00064** — cost of one question answered
>
> A small footnote line, deliberately understated: **"Measured from live API usage, not
> estimated."**
>
> That footnote is doing real work — design it so it reads as quiet confidence rather
> than fine print. The whole slide should feel like evidence being placed on a table.

---

## Slide 8 — the evidence

> Next screen. Restrained and technical.
>
> Dominant figure: **89/89** with a line beneath: *checks passed, across six notebook
> formats.*
>
> Below, six small labelled tiles representing the formats tested: *Column table* ·
> *No header row* · *Free-text list* · *Event diary* · *Tally sheet* · *Afrikaans form*
>
> One line: **"It reads notebooks it has never seen."**
>
> Keep this one plain. It's a credibility beat between two emotional slides, and it
> should feel like a lab result, not a marketing claim.

---

## Slide 9 — honest status

> Next screen. Two columns, deliberately equal in visual weight — the honesty is the
> point, so don't shrink the right column.
>
> Left, **"Working today"**: Livestock register · Notebook scan · 5 languages · Voice
> conversation · Works offline · Namibian vaccination schedules · Real field data
>
> Right, **"Known gaps"**: Oshiwambo speech recognition is weak — no training data
> exists · Voice accents need native tuning · No API auth yet · No SMS gateway
>
> Do not style the right column as a warning or a problem — no red, no alert icons. It
> should read as a team that knows exactly where it stands. Calm and matter-of-fact.

---

## Slide 10 — close

> Final screen. The quietest slide in the deck.
>
> One line, large, centred, with room to breathe:
>
> **"The notebook was never the problem. Nobody had bothered to read it."**
>
> Beneath it, small: **VeldWys** and the team name.
>
> Almost no other elements. Let the sentence sit. This is the last thing on screen
> while questions are asked, so it needs to survive several minutes of being looked at.

---

## If Stitch struggles

- **Too much at once** — it degrades on multi-screen prompts. One slide per prompt.
- **Drifting off the system** — re-anchor with *"same design system as the previous
  screens: same palette, same type scale, same slide skeleton."*
- **Treating it like an app** — if it adds navigation bars, buttons, or menus, say
  *"this is a presentation slide, not an app screen — no navigation, no interactive
  controls."*
- **Table slides (6 and 7)** are where Stitch is weakest. If they come back poor,
  generate the palette and type scale from Stitch and build those two by hand.
