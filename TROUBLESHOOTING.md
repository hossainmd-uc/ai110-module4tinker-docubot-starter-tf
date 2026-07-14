# DocuBot Troubleshooting Guide

Quick-reference for issues you're likely to hit, in rough order of when you'll see them.

- **Section 1** = starter code as given (`llm_client.py` is complete) — exact file/line fixes.
- **Sections 2-4** = design decisions inside `build_index`/`score_document`/`retrieve`, which start as empty TODO stubs. Nothing there exists in your file yet — these are things you'll likely run into while writing your own version, not bugs to hunt for.

---

## 1. Model errors (start here)

Hardcoded model name: [llm_client.py:20](llm_client.py#L20)

```python
GEMINI_MODEL_NAME = "gemma-4-31b-it"
```

Free-tier model availability changes over time — don't assume the code is broken before checking this.

**`404 NOT_FOUND ... not supported for generateContent`**
- Cause: the model name is invalid, deprecated, or a family not served via `generateContent`.
- Fix: swap in a current model at [llm_client.py:20](llm_client.py#L20):

| Model ID | Notes |
|---|---|
| `gemini-2.5-flash` | Solid default, free-tier eligible |
| `gemini-2.5-flash-lite` | Cheaper/faster, lower quality |
| `gemini-2.5-pro` | Higher quality, tight free-tier limits |
| `gemma-4-31b-it` | Current default — Gemma, not Gemini |

If none work, check Google AI Studio for what your account currently has access to.

**`403 PERMISSION_DENIED: Your project has been denied access`**
- Cause: account/project-level block — **not** fixed by changing the model name.
- Fix: confirm your key is active in [Google AI Studio](https://aistudio.google.com/apikey), check billing/API-enablement on the linked project, try regenerating the key, or check regional restrictions.

**`Missing GEMINI_API_KEY environment variable`**
- Cause: no `.env` file, or it's missing the key.
- Fix: add `GEMINI_API_KEY=your_key_here` to a `.env` file in the project root. Without it, modes 1 and 3 are disabled but mode 2 still works.

---

## 2. Word-form mismatches (e.g. "endpoint" vs. "endpoints")

- Symptom: a question like "Which endpoint returns all users?" returns nothing or the wrong doc, even though `API_REFERENCE.md` clearly covers it — because the doc says "endpoint**s**" and your matcher does exact word comparison.
- Why it matters: this isn't an edge case — plural/tense mismatches ("generate" vs. "generated") show up in nearly every real question.
- No single required fix — a few options, in increasing order of effort:
  - **Do nothing yet.** If this hasn't bitten you, it's fine to leave exact matching and revisit only if you notice retrieval quietly missing things.
  - **Hand-roll a basic suffix rule** (e.g. strip a trailing "s"/"es" before comparing). Zero dependencies, a few lines, catches plain plurals. Downside: can misfire on words that end in "s" naturally (e.g. "status").
  - **Use a stemming library** (e.g. NLTK's `PorterStemmer`). Handles plurals plus suffixes like "-ing"/"-ed"/"-tion" more correctly than a hand-rolled rule, at the cost of an extra dependency (`pip install nltk`, add `nltk>=3.8` to `requirements.txt`; if you see `ModuleNotFoundError: No module named 'nltk'`, this is why). No separate data download needed for this specific stemmer.
- Whichever you pick, apply it consistently to both the query and the document text you're comparing against — mismatched treatment on either side defeats the fix.
- Quick check: run whatever word-normalizing step you land on against two related word forms from your docs — if the outputs differ, that mismatch will silently break retrieval.

---

## 3. Retrieval returns whole files instead of snippets

- Symptom: mode 2 dumps an entire `.md` file as one "snippet" instead of a focused excerpt.
- Cause: a first-pass `retrieve()` that returns whole `(filename, text)` pairs — "top_k" ends up meaning whole files, not passages. This is the expected next problem to solve, not a bug.
- Fix — two-stage retrieval:
  1. Score every whole document, pick the single best-scoring one.
  2. Split *only that document* into paragraphs (e.g. on blank lines), score each paragraph the same way, return the top-scoring ones.
- Watch for: a bare heading line (`## Token Generation`) becoming its own empty "chunk" — glue it onto the paragraph that follows instead.

---

## 4. Threshold tradeoff: false answers vs. false refusals

Only relevant if you add a relevance guardrail — optional, not required.

- Problem A — confident nonsense answers: a query like "Where is the apple generated?" (word appears nowhere in docs) can still score well on some document just from common words ("the", "is") appearing often.
- Common fix: strip stopwords, then require some minimum fraction of the *meaningful* query words to appear before allowing any score.
- Problem B this fix can cause — false refusals: a real, answerable question (e.g. "How does a client refresh an access token?", answered in `AUTH.md`) gets refused if the answer is split across two adjacent paragraphs and neither alone clears the threshold.
- The tradeoff: tightening the threshold reduces false answers but increases false refusals, and loosening it does the reverse — no single value eliminates both. Worth exploring: scoring a sliding window of adjacent paragraphs, or relaxing the threshold when the whole-document score is very high.

---

## Quick Diagnostic Checklist

1. Nothing answers / crashes on startup → check `.env` has `GEMINI_API_KEY` → Section 1.
2. Naive or RAG mode fails, retrieval works fine → LLM/API issue → Section 1.
3. `retrieve()` misses a document you know is relevant → word-form mismatch → Section 2.
4. `ModuleNotFoundError: nltk` → install it → Section 2.
5. `retrieve()` returns whole files → needs chunking → Section 3.
6. Guardrail refuses a question the docs do answer → threshold tradeoff → Section 4.
