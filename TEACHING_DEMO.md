# DocuBot Demo Guide (Teaching Fellow Reference)

This is a "Finished Product First" demo script for walking students through DocuBot. It's built from the actual build process for this repo — the real errors hit, the real design calls made, and the real failure cases discovered. Use it as a reference during the session, not a script to read verbatim.

Core rule for the whole session: **show, ask, pause, hint, only then explain.** Resist the urge to fill silence or jump to code.

---

## THE 5–7 MINUTE VERSION (use this — the rest of the doc is backup material)

Everything below this section is the full 38-minute walkthrough, kept for prep/reference and for follow-up questions if students go deep. **This is the actual script to run.** It has two halves: an interactive comparison of all three modes on one shared question (~4 min), then a rapid-fire recap of the real hurdles hit while building this (~2 min). Hard rule: **no single talking block longer than 30 seconds, never more than 60.** If you're about to explain for a full minute, stop and ask a question instead.

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

## FULL VERSION (backup / if time allows)

---

## 0. Before You Start

Have these ready in separate terminal tabs / windows so you can move fast without fumbling:

- A terminal in the project root with `python main.py` ready to run.
- The `docs/` folder open in the editor (AUTH.md, API_REFERENCE.md, DATABASE.md, SETUP.md) — students should be able to see these are plain markdown files, not magic.
- [docubot.py](docubot.py) open but collapsed/scrolled to the top — don't show the implementation yet.
- [model_card.md](model_card.md) open in a tab — you'll reference specific findings from it, not read it aloud.

Do **not** open [llm_client.py](llm_client.py) yet — the model-name story is a mid-demo beat, not a pre-brief.

---

## 1. Start With the Final Output (0:00–3:00)

Say: **"Before we look at any code, let me show you what we're building today."**

Run mode 3 (RAG) live with a real question:

```
Enter choice: 3
Or type a single custom query: Where is the auth token generated?
```

Let them see the actual output:

```
The auth token is generated by the `generate_access_token` function in the `auth_utils.py` module.

Source: AUTH.md
```

Then run it again with a question that should legitimately fail:

```
Or type a single custom query: Where is the apple generated?
```

```
I don't have enough information to answer that.
```

**Why show both in the first three minutes:** students need to see it work *and* see it correctly refuse before they start caring about mechanism. The refusal is what makes the first answer trustworthy — call that out explicitly once, then move on.

> Pause here. Let it sit for a few seconds before talking again.

---

## 2. The Thought-Provoking Question (3:00–5:00)

Ask: **"What do you think the program needed to know in order to answer that first question correctly, and to refuse the second one?"**

**Embrace the silence.** Wait 5–10 seconds. Do not fill it.

If nobody answers, drop hints one at a time, pausing between each:
- "Maybe... it read something?"
- "Maybe it knows which file to look in?"
- "Maybe it's checking whether the question is even related to the docs at all?"

**Cold call fallback:** if the room stays quiet, pick a student directly: *"[Name], if you had to guess — does this look like it read the actual project docs, or does it sound like it's guessing from general knowledge?"*

Keep this high-level. Don't explain retrieval yet — let their answers steer how deep you go next.

---

## 3. Hurdle #1: The Model Kept Rejecting Us (5:00–10:00)

This is a real hurdle from building this project, and it's a great one to demo because it's not really about code — it's about how fast the ecosystem underneath an app can shift, and why hard-coding a model name is a design decision, not a throwaway detail.

**Show the sequence of errors we actually hit, in order:**

1. First attempt: `gemma-3-27b-it`
   ```
   404 NOT_FOUND: models/gemma-3-27b-it is not found for API version v1beta,
   or is not supported for generateContent.
   ```
2. Switched to `gemini-2.5-flash` — fixed the 404, but then:
   ```
   403 PERMISSION_DENIED: Your project has been denied access.
   ```
3. That 403 turned out to be an **account/project-level** issue (billing/region/flagged project), not a model-name issue — switching models again wouldn't have fixed it on its own.
4. Final model landed on: **`gemma-4-31b-it`** (Gemma 4, released after this class's Gemini 2.5-era knowledge — a good live example that "the newest model" is a moving target you have to verify, not assume).

**Ask:** *"Why didn't switching the model name fix the second error?"*

Pause. Let them reason about the difference between "the model doesn't exist" (404) vs. "you're not allowed to use anything" (403) — these are different layers of the stack failing.

**Fallback if silent:** "Does a 404 and a 403 sound like the same kind of problem to you, or different ones?"

**The real lesson to land:** a single hardcoded constant —

```python
GEMINI_MODEL_NAME = "gemma-4-31b-it"
```

— in [llm_client.py](llm_client.py) is doing a lot of invisible work. Free-tier model availability changes over time, and a project built today may need this constant updated in six months. This is worth calling a "hurdle," not a "bug": it's not something they'll fix once and never see again in real work.

**Real-world connection:** every product built on a hosted LLM API has this exact fragility — model names get deprecated, rate limits change, accounts get flagged. This isn't a toy-project quirk.

---

## 4. Hurdle #2: What Does "Naive" Even Mean Here? (10:00–15:00)

Run mode 1 (naive LLM) live on the same question from the opening demo:

```
Enter choice: 1
Or type a single custom query: Where is the auth token generated?
```

Show the output — a long, confident, generic answer listing 3–4 possible auth architectures (OAuth IdP, custom backend, API keys, sessions), never once mentioning this project.

**Ask:** *"This sounds smart and thorough. What's actually wrong with it?"*

Pause 5-10 seconds.

**Hints if silent:**
- "Did it mention `auth_utils.py` anywhere?"
- "Did it mention *this* project at all?"
- "What do you think this mode was actually given as input — just the question, or the question plus the docs?"

**The reveal:** open [llm_client.py](llm_client.py) and show `naive_answer_over_full_docs`:

```python
def naive_answer_over_full_docs(self, query, all_text):
    # We ignore all_text and send a generic prompt instead
    prompt = f"""
You are a documentation assistant. 
Answer this developer question: {query}
"""
```

Point out: `all_text` — the entire docs corpus — is passed in as a parameter and never used. This is deliberate: it's the "naive" baseline precisely because it shows what an LLM does with **zero grounding**, even though it *could* have been given the docs.

**Ask a harder follow-up:** *"If this looked *this* confident while being wrong about a toy project, what happens when a developer asks a similarly-confident-sounding LLM about your production auth system?"*

Let that land. Don't answer it for them.

**Real-world connection:** this is the entire reason RAG exists as a pattern — LLMs are fluent regardless of whether they're right, and fluency is not evidence.

---

## 5. Hurdle #3: From Scoring One Document to Ranking All of Them (15:00–22:00)

This is the core "sticking point" of the whole assignment — worth spending real time here rather than rushing to the finished `retrieve()`.

Run mode 2 (retrieval-only):

```
Enter choice: 2
Or type a single custom query: Which endpoint returns all users?
```

Show the output — the raw retrieved paragraph, `### GET /api/users`, labeled `[API_REFERENCE.md]`.

**Ask:** *"Before I show you the code — if you had to write a function that scores just ONE document against a query, what would it even measure?"*

Pause. This is a genuine design question, let them propose things: word overlap, word count, exact phrase match.

**Fallback:** "Does this look like it just counted how many words from the question showed up in the document?"

Once they've proposed something like word-overlap counting, **ask the harder question that's the actual hurdle**:

*"Okay — now say you can score one document. What's different about picking the best one out of four documents? What's different about picking the best *paragraph* inside the best document?"*

Pause again. This is the two-stage design that isn't obvious until you've hit the problem yourself:

1. Score every whole document, pick the single highest scorer.
2. *Then* split just that one document into paragraphs and score those separately.

**Ask why you'd bother with two stages instead of just scoring every paragraph in every document directly.** Let them guess (fewer false cross-document matches; keeps snippets coherent to one source) before you explain it yourself.

**Discuss the decision, not the solution:** don't show them `chunk_document`'s regex. Instead frame the actual design tension we hit: markdown files mix headers, paragraphs, code blocks, and bullet lists — how do you turn that into clean "paragraph" units without either (a) treating a bare header as its own useless mini-chunk, or (b) merging so much together that a chunk is basically the whole file again? Ask: *"What would you do with a line that's just `## Token Generation` and nothing else?"*

---

## 6. Hurdle #4: The Word Problem — "Endpoint" vs. "Endpoints" (22:00–27:00)

Live demo this exact bug, since it's genuinely instructive:

Show that `API_REFERENCE.md` uses the word "**endpoints**" (plural) in places, but a student query like *"Which endpoint returns all users?"* uses "**endpoint**" (singular). Point out that a plain word-count scorer treats these as two completely different words.

**Ask:** *"If your scoring function just checks 'does this exact word appear,' what happens when the doc says 'endpoints' and the question says 'endpoint'?"*

Pause.

**Fallback:** "Does this look like it considered these to be the same word, or two different words?"

**Reveal the fix:** stemming (`PorterStemmer` from `nltk`) reduces both "endpoint" and "endpoints" down to the same root, `endpoint`, before comparing. Show it live if you want:

```python
>>> bot.tokenize("endpoint")
['endpoint']
>>> bot.tokenize("endpoints")
['endpoint']
```

**Ask a design-decision question, don't just hand over the answer:** *"We could have hand-written a rule like 'strip a trailing s off every word.' What might go wrong with that instead of using a real stemming library?"*

Let them get to: words that end in "s" naturally (e.g. "status") would get mangled ("statu"). This was a real decision made mid-build — a naive suffix-stripper vs. a real stemmer — worth presenting as a genuine tradeoff discussion (dependency cost vs. correctness), not a foregone conclusion.

---

## 7. Hurdle #5: When Should the System Say "I Don't Know"? (27:00–34:00)

This is the richest design-decision section — spend real time here.

**Demo the false positive first.** Run mode 2 or 3 with:

```
Where is the apple generated?
```

Show it correctly refuses. Then reveal *why* it almost didn't:

**Show the raw scores** (you can print these live or reference them):

| File | Score |
|---|---|
| AUTH.md | 34 |
| SETUP.md | 31 |
| API_REFERENCE.md | 12 |
| DATABASE.md | 16 |

**Ask:** *"'Apple' doesn't appear anywhere in these docs. Why did AUTH.md still score 34 — higher than everything else?"*

Pause.

**Hints:** "What other words were in that question besides 'apple'?" → lead them to notice "where," "is," "the," "generated" are all common words that show up constantly regardless of topic.

**The fix:** a stopword list (the, is, a, where, which...) filters those common words out before scoring, and a **coverage threshold** requires that *more than half* of the remaining meaningful words in the query actually appear in the text — otherwise the score is forced to zero, no matter how many common words matched.

**Now demo the false negative this same threshold causes** — this is the most valuable moment in the whole demo, because it's a real, still-unresolved limitation, not a solved problem:

```
How does a client refresh an access token?
```

Show that this **also refuses** — "I don't have enough information to answer that" — even though AUTH.md's "Client Workflow" section literally documents `/api/refresh`.

**Ask:** *"AUTH.md scored 36 out of a possible maximum for this exact question — full marks, basically. So why did it still refuse?"*

Pause 5-10 seconds — this one is hard, let it sit.

**Fallback:** "The answer is written across two different, back-to-back paragraphs, not one paragraph. Does that give you a hint about why a per-paragraph threshold might fail here?"

**The reveal:** the coverage check runs on each individual paragraph *after* the winning document is chosen — and the real answer is split across two adjacent list items ("...access token in the response" / "...calling `/api/refresh`"). Neither paragraph alone contains enough of the query's key words to pass the bar, even though the document as a whole clearly does.

**Ask the open design question, and don't answer it for them:** *"How would you fix this without breaking the apple case we just fixed?"* Let them propose ideas (merging adjacent paragraphs, scoring a sliding window of paragraphs, lowering the threshold, scoring by document instead of paragraph). There is no single right answer here — that's the point.

**Real-world connection:** this is exactly the kind of recall/precision tradeoff that real production RAG systems fight constantly — tightening the filter to kill hallucinations always risks silently killing correct answers too, and there's no free lunch.

---

## 8. Wrap: The Three Modes as a Progression (34:00–38:00)

Bring it back to the finished product from Step 1. Ask, one more time, with everything they've now seen:

**"Given everything we just walked through, when would you trust naive mode? Retrieval-only? RAG?"**

Pause. Let a few students answer this time — they should have real material now.

Points to make sure land, in your own words based on how the discussion goes:
- **Naive** never knows this project exists — it's a general-knowledge chatbot wearing a documentation-assistant costume. Fluent, sometimes wrong, never uncertain about being wrong.
- **Retrieval-only** never lies, but never explains either — it hands you the raw evidence and makes you do the reading.
- **RAG** is only as good as retrieval underneath it — when retrieval nails it, RAG is the best of both; when retrieval whiffs (Section 7's refresh-token case), RAG can't rescue it, but at least it won't guess.

**Real-world connection to close on:** Spotify-style recommenders, coding assistants, support chatbots — every one of them is making some version of the same choice at every layer: how much do you trust the model to know things on its own vs. how much do you force it to show its work? Ask them to sit with the question: *"Where else have you seen a system make this same tradeoff — sometimes without telling you?"*

---

## Quick Reference: All Questions in This Guide

Use this as a cheat-sheet during the actual session so you don't have to scroll.

| Section | Primary question | Fallback if silent |
|---|---|---|
| 2 | What did the program need to know to answer correctly and refuse correctly? | Does this look like it read the docs, or is it guessing? |
| 3 | Why didn't switching the model name fix the 403? | Does a 404 and a 403 sound like the same kind of problem? |
| 4 | This sounds smart — what's actually wrong with it? | Did it mention this project at all? What was it actually given as input? |
| 5 | What would a one-document scoring function even measure? | Does this look like it just counted overlapping words? |
| 5 | Why two stages (document, then paragraph) instead of scoring every paragraph directly? | — |
| 5 | What would you do with a line that's just a bare markdown header? | — |
| 6 | What happens when the doc says "endpoints" and the question says "endpoint"? | Does this look like it considered these the same word? |
| 6 | What could go wrong with a hand-written "strip trailing s" rule? | — |
| 7 | Why did AUTH.md score highest for a question about "apples"? | What other words were in that question besides "apple"? |
| 7 | AUTH.md scored full marks here — why did it still refuse? | The answer spans two paragraphs, not one — does that help? |
| 7 | How would you fix this without breaking the apple case? | — |
| 8 | When would you trust naive vs. retrieval-only vs. RAG? | — |

---

## Things Deliberately Left Out of This Demo

Don't get pulled into these unless a student specifically asks — they're implementation detail, not the conceptual hurdles:

- The exact regex used in `tokenize()` / `chunk_document()`.
- How `python-dotenv` loads `.env`.
- The exact NLTK API surface (`PorterStemmer.stem()`).
- `build_index`'s inverted-index structure — it's real Phase 1 work, but `retrieve()` doesn't currently use it, so it's a side note, not core to the demo's narrative.
