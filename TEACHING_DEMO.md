# DocuBot Demo Guide (Teaching Fellow Reference)

This is a "Finished Product First" demo script for walking students through DocuBot. It's built from the actual build process for this repo — the real errors hit, the real design calls made, and the real failure cases discovered. Use it as a reference during the session, not a script to read verbatim.

Core rule for the whole session: **show, ask, pause, hint, only then explain.** Resist the urge to fill silence or jump to code.

---

## THE 5–7 MINUTE DEMO SCRIPT

This is the actual script to run — capped at 8 minutes, no full-length alternative. It has two halves: an interactive comparison of all three modes on one shared question (~4 min), then a rapid-fire recap of the real hurdles hit while building this (~2 min). Hard rule: **no single talking block longer than 30 seconds, never more than 60.** If you're about to explain for a full minute, stop and ask a question instead.

**Setup:** terminal ready with `python main.py`, `docs/` folder visible, `docubot.py` open but not scrolled to implementation.

---

### Half 1 — Interactive mode comparison (~4:00)

**0:00–0:25 — Preface (one breath, no pause here).**
Say, close to verbatim: *"DocuBot is a small documentation assistant that answers developer questions about a codebase. It has three modes: naive LLM, which sends the whole docs corpus to Gemini and asks it to answer; retrieval only, which uses indexing and scoring to pull relevant snippets with no LLM involved; and RAG, which retrieves snippets first, then asks Gemini to answer using only those. The docs folder has realistic developer files — API reference, auth notes, database notes — just plain text, no backend needed."*

**0:25–2:15 — Run all three modes live, same question, back to back.**
Type `Where is the auth token generated?` into mode 1, then mode 2, then mode 3, letting each finish before starting the next. Narrate in a half-sentence between runs, nothing more — *"okay, that's naive... now retrieval only... now RAG"* — the outputs do the talking, not you.

**2:15–2:45 — Ask: "What information do you think each mode used to come up with its answer?"**
Pause 3–5 seconds. Hints if silent, one at a time:
- *"Does the naive answer look like it read any of our files, or is it guessing from general knowledge?"*
- *"What do modes 2 and 3 have in common that mode 1 doesn't?"*

Let a student land on: naive mode never sees the docs at all; retrieval and RAG both pull from `AUTH.md` specifically.

**2:45–3:45 — Ask: "Retrieval mode returns just this one paragraph — any guesses how you'd narrow a whole document down to just the right paragraph?"**
Pause 3–5 seconds. Hint if silent: *"What's in a markdown file you could split on — headings? Blank lines between paragraphs?"* You don't need the full reveal here — just let them propose an idea (split by headers, split by blank lines, score each piece). You'll confirm the actual answer in Half 2.

---

### Half 2 — Rapid hurdle recap (~2:00, four beats, ~30s each)

**Beat 1 — The model kept rejecting us.**
*"Quick one — getting the LLM call working took a few tries. Hit a 404 on one model name, then a 403 on the next that turned out to be an account-access issue, not a model issue. Landed on `gemma-4-31b-it`. Point being: the model name here isn't a fixed fact, it's something you have to verify, because it can change under you."*

**Beat 2 — Confirm the paragraph-narrowing design decision.**
*"Following up on your guesses — yes, that's basically it. We score every whole document first, pick the single best one, then split just that one file into paragraphs on blank lines and score those separately. Originally retrieval mode just returned the entire best-matching file — going from 'best document' to 'best paragraph inside the best document' was the hardest part of this whole build."*

**Beat 3 — The word problem.**
*"One more: `API_REFERENCE.md` says 'endpoints,' plural — but someone might ask about 'endpoint,' singular. A plain word-match sees those as two different words. We fixed it by running every word through a stemming library, NLTK's Porter stemmer, so 'endpoint' and 'endpoints' both reduce to the same root before comparing."*

**Beat 4 — One hurdle left for them.**
*"There's one more design tradeoff in here — about when the system should say 'I don't know' — that I'll let you find on your own. I'll send around the write-up with all of this if you want to dig in."* Send `model_card.md` (and this file, if useful) after class. Do not explain the refusal tradeoff live in this version — it's the one genuinely open, unresolved question, and it's better discovered than told.

---

### Cheat Sheet (for live use)

| Timestamp | Question | Fallback hint |
|---|---|---|
| 2:15 | What information do you think each mode used? | Does naive mode look like it read our files? What do modes 2 & 3 share that mode 1 doesn't? |
| 2:45 | How would you narrow a whole document to just the right paragraph? | What's in a markdown file you could split on — headings, blank lines? |

Beats 1–4 in Half 2 are statements, not questions — say them, don't pause for answers, keep moving.

---

## Things Deliberately Left Out of This Demo

Don't get pulled into these unless a student specifically asks — they're implementation detail, not the conceptual hurdles:

- The exact regex used in tokenizing/chunking.
- How `python-dotenv` loads `.env`.
- The exact NLTK API surface (`PorterStemmer.stem()`).
- The inverted-index structure from `build_index` — real Phase 1 work, but `retrieve()` doesn't use it directly, so it's a side note, not core to the demo's narrative.
