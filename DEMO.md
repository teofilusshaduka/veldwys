# VeldWys: 5-minute demo script

**Setup before you start**

```bash
python seed_demo.py                              # demo / demo. Okatope Farm, Omaheke
uvicorn main:app --host 0.0.0.0 --port 8001      # keep this terminal visible
tailscale serve --bg 8001                        # phone URL over HTTPS
```

Phone: open the Tailscale URL, **Add to Home Screen**, launch from the icon so it's full-screen with no browser chrome. Sign in as `demo` before you present, start the demo already logged in.

Have on hand: the phone (mirrored to the screen if possible) and the laptop showing the terminal log.

---

### 0:00. The problem (25 s)

> "Bush encroachment and overgrazing are the biggest threats to Namibian livestock farming. There's an excellent open dataset for it, satellite data paired with real field measurements. But a farmer in Omaheke can't read a CSV.
>
> The obvious build is a chatbot over that dataset. We started there and hit a wall: every question needs herd size, camp size, location. The farmer types their numbers in again, and again, and again. That's not an advisor, that's a form.
>
> So we built the farm system first, and put the agent on top of it."

### 0:25. It already knows the farm (40 s)

Open the app on the phone. Dashboard is showing.

> "This is Okatope Farm, 1,800 hectares in Omaheke. 90 animals, 58.5 large stock units, and VeldWys already knows that, because it manages the register.
>
> Top of the screen: what needs attention. A red alert, the anthrax booster for the cattle herd is overdue. And an amber one: dry season, 3 mm of rain in 60 days, so the veld won't regrow yet. Nobody asked for those. They're computed every time the app opens, and they cost nothing, no AI call."

Tap the Herd tab, scroll.

> "Every animal individually. Ear tag, breed, sex, birth date, status."

### 1:05. Ask it something real (50 s)

Tap the red alert card, it drops the question straight into chat.

> "Tapping an alert asks the agent about it."

While it answers:

> "It's reading the farm's own register, no herd size typed in."

Then tap the chip **"Compare my pasture to last year"**.

> "This is the one I'd point at. This answer comes from the *real* dataset, actual field measurements at monitoring sites visited in February 2023 and again in February 2024. Same sites, same month, so it's a like-for-like comparison."

Open **How I worked this out**.

> "Every answer shows its work: which tool ran, which dataset answered, the actual numbers. When our two weather sources disagree it reports a range instead of quietly averaging them."

### 1:55. Voice, in the farmer's language (45 s)

Switch language to Afrikaans in the header. UI changes.

> "The whole interface, not just the chat, four languages: English, Afrikaans, Oshiwambo, Otjiherero."

Hold the mic button and ask in Afrikaans: *"Moet ek my beeste skuif?"*

> "Speech to text, and the answer comes back spoken."

Now switch to Oshiwambo and play the morning briefing.

> "This is the bit I'm proudest of. No text-to-speech engine has an Oshiwambo voice, and the naive version said the sentence in Oshiwambo but read the numbers in English, which a native speaker hears immediately. We tried getting a model to write the numerals and it invented words. So the Oshiwambo and Otjiherero number systems are built properly in code. Fifty-three is omilongo ntano na yatatu. Every word you just heard is in the language."

Tap the headphone icon for conversation mode.

> "And this is hands-free. It listens, hears me stop, answers out loud, then listens again. That's the realistic mode when you're standing in a camp with your hands full."

### 2:40. It keeps the records for you (40 s)

Type or say: *"I sold three goats at the auction today for about N$1,800 each."*

> "This is the part I'd argue matters most. It didn't just log that, it marked three goats sold in the register and read back which ear tags it chose, so I can correct it. No farmer is going to open a form and tick three animals."

Then ask: *"What are my goats worth?"*

> "Prices come from a reference table, not the model's imagination. It says they're indicative and tells me to confirm at my own auction. On a sale decision, an invented number is the worst thing this app could do."

### 3:20. The notebook (40 s)

Dashboard → **Scan notebook**. Photograph a handwritten page.

> "This is how the farm actually keeps records today. This is my family's notebook.
>
> It reads the handwriting. Afrikaans included, works out that *Boerbok* is a goat and *ooi* is a ewe, and flags what it wasn't sure about.
>
> Nothing is saved automatically. The farmer checks every record first, because a livestock register is a legal document under NamLITS traceability."

Confirm the import; the herd count updates.

### 4:00. Insights (25 s)

Tap the Insights tab.

> "Stocking against what Omaheke is guided to carry. Herd movement, losses, health-calendar compliance. And this line is the real dataset: grass cover falling while bare ground rises, measured at a monitoring site near this farm across four visits. The agent reads these same numbers, so its advice can cite the trend instead of guessing."

### 4:25. Offline + honesty (35 s)

Turn on airplane mode. Reopen the app.

> "Farms are remote and data is expensive. Offline, the register and dashboard still open. Anything you record queues and syncs when you're back in signal."

Turn connectivity back on.

> "And what it won't do: those monitoring sites are near the farm, not measurements of this farm's camp, it says so every time. During the dry season it refuses to quote a rainfall percentage, because 'plus 97 percent' against a 1.7 mm normal is a 3 mm shower, not good news. And it won't give veterinary diagnosis, animal health emergencies go to the state vet."

### 5:00. Close (15 s)

> "The dataset exists. VeldWys turns it into advice a farmer can act on, grounded in their own herd, in their own language, on the phone in their pocket, with or without signal."

---

## Backup plan

- **Live demo fails** → play the recorded video (record one beforehand and keep it open in a tab).
- **Wi-Fi dies** → this is the offline demo. Open the app anyway and narrate it as the feature it is.
- **Judge asks about failover** → stop the OpenAI key in `.env`, restart, ask again: the same conversation continues on Claude Haiku. The provider badge is in the chat response payload.

## Questions to expect

**"Did you use the real dataset?"**. Yes, both. `archive/` holds the actual field forms; `prepare_real_data.py` extracts cover, perennial grass, bush encroachment, bare ground and standing crop from 21 sites across 4 seasonal visits. The synthetic starter set provides regional carrying capacity for any region a farmer pins. The agent reports which one answered.

**"What does it cost to run?"**. Chat is `gpt-4o-mini`, cents per demo day. All alerts are rules, not model calls. Weather is cached 6 hours per location. The only premium call is notebook OCR on `claude-sonnet-5`, which happens rarely and is worth it for handwriting.

**"What happens if OpenAI goes down?"**. Automatic failover to Anthropic mid-conversation, with the history translated between provider formats.

**"Is this secure enough for real farms?"**. No, and we say so in the technical docs. SHA-256 without salting and no session tokens is prototype-grade; production needs argon2 and real sessions.
