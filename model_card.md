# DocuBot Model Card

This model card is a short reflection on your DocuBot system. Fill it out after you have implemented retrieval and experimented with all three modes:

1. Naive LLM over full docs  
2. Retrieval only  
3. RAG (retrieval plus LLM)

Use clear, honest descriptions. It is fine if your system is imperfect.

---

## 1. System Overview

**What is DocuBot trying to do?**  
Describe the overall goal in 2 to 3 sentences.

> DocuBot is a small documentation-question-answering assistant for a sample project's `docs/` folder (auth, API reference, database, setup). It demonstrates three escalating strategies for answering developer questions — asking an LLM with no context, retrieving relevant text with no LLM, and combining both — so the tradeoffs of each approach are visible side by side.

**What inputs does DocuBot take?**  
For example: user question, docs in folder, environment variables.

> A free-text developer question (via CLI prompt or `dataset.py` sample queries), the `.md`/`.txt` files in `docs_folder` (loaded once at startup into `self.documents`), and, for LLM-backed modes, a `GEMINI_API_KEY` environment variable used to construct a `GeminiClient`.

**What outputs does DocuBot produce?**

> Mode 1 and Mode 3 output a natural-language answer string from Gemini. Mode 2 outputs the raw retrieved paragraph(s), each labeled with its source filename (e.g. `[AUTH.md]`). All three modes can also output a refusal string when no answer is available — either an LLM-authored refusal ("I do not know based on the docs I have.") or DocuBot's own guardrail message ("I don't have enough information to answer that.").

---

## 2. Retrieval Design

**How does your retrieval system work?**  
Describe your choices for indexing and scoring.

- How do you turn documents into an index?
- How do you score relevance for a query?
- How do you choose top snippets?

> **Indexing (`build_index`):** each document's text is tokenized (see below) and a tiny inverted index is built: `{token: [filenames containing it]}`, deduped per document. This index isn't currently consulted by `retrieve()` itself — with only 4 documents, scoring every document directly was simpler and fast enough — but it's a demonstrable Phase 1 artifact and would let a future version narrow candidates before scoring at larger scale.
>
> **Tokenization (`tokenize`):** lowercase the text, extract alphanumeric runs via regex, drop a hardcoded `STOPWORDS` set (the, is, a, where, which, ...), then stem each remaining token with NLTK's `PorterStemmer`. Stemming was added specifically after we noticed the query "Which endpoint returns all users?" failed to match `API_REFERENCE.md`'s "### GET /api/users" section because the doc used the plural "endpoints" — stemming folds both to `endpoint`. Stopword removal was added after noticing that queries built mostly of common words (e.g. "Where is the apple generated?") still produced high scores purely from "the"/"is" appearing frequently in unrelated documents.
>
> **Scoring (`score_document`):** tokenize both the query and the candidate text, count text token frequencies with a `Counter`, and require that *more than half* of the distinct query tokens appear in the text at all (`MIN_QUERY_COVERAGE = 0.5`, checked as `coverage <= 0.5` fails) — otherwise the score is forced to 0 regardless of raw word overlap. If coverage passes, the score is the summed term frequency of each query token found in the text.
>
> **Choosing snippets (`retrieve`):** retrieval is two-stage. First, every whole document is scored and the single highest-scoring one is selected (documents scoring 0 are excluded, and if none score above 0, `retrieve` returns `[]`). Second, that one winning document is split into paragraph-level chunks (`chunk_document`, splitting on blank lines, with a lone markdown heading line glued onto the paragraph that follows it so headers act as context rather than empty chunks). Each chunk is scored the same way, and the top `top_k` (default 3) highest-scoring chunks from *that single document* are returned as `(filename, chunk_text)` pairs.

**What tradeoffs did you make?**  
For example: speed vs precision, simplicity vs accuracy.

> - **Single-document scoping:** restricting chunk retrieval to only the single best-scoring document is simple and avoids mixing snippets from unrelated files, but it means a genuinely cross-cutting question (e.g. one that needs both AUTH.md and API_REFERENCE.md) can never retrieve evidence from the second-best document, even if it also scored well.
> - **Unnormalized term-frequency scoring:** summed counts favor longer text over more precisely relevant text. This is mitigated at the chunk level (paragraphs are roughly similar in length) but is still visible at the document level, where a long file can outscore a short, highly relevant one purely on bulk.
> - **Coverage threshold as a blunt gate:** requiring >50% of distinct query terms to appear in a *single* chunk is a simple, effective filter against irrelevant documents (see the "apple" case below), but it also rejects legitimate answers that are split across two adjacent paragraphs (see Failure Case 2) — precision against nonsense queries was bought at the cost of recall on legitimately fragmented answers.
> - **No cross-encoder/embedding similarity:** this is bag-of-words lexical matching only. It's fast, dependency-light (aside from NLTK's stemmer), and fully interpretable, but it has no notion of synonyms or paraphrase (e.g. "list users" vs. "return all users" only work because both literally share the word "users"/"return(s)").

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**  
Briefly describe how each mode behaves.

- Naive LLM mode: Always calls Gemini (`naive_answer_over_full_docs`) with just the raw question — the full corpus text is loaded via `full_corpus_text()` but is deliberately never included in the prompt, so the model answers from its own general knowledge only.
- Retrieval only mode: Never calls the LLM. Purely returns `retrieve()`'s top paragraphs, formatted with filename labels, or the guardrail refusal string if nothing clears the relevance threshold.
- RAG mode: Calls the LLM (`answer_from_snippets`), but only with the snippets `retrieve()` selected — if `retrieve()` returns `[]`, the LLM is never invoked and DocuBot returns the guardrail refusal directly.

> Naive mode is intentionally the "no grounding" baseline; retrieval mode is the "no synthesis" baseline; RAG combines both, but its ceiling is capped by whatever `retrieve()` handed it — RAG cannot answer with evidence retrieval failed to surface.

**What instructions do you give the LLM to keep it grounded?**  
Summarize the rules from your prompt. For example: only use snippets, say "I do not know" when needed, cite files.

> The RAG prompt (`llm_client.answer_from_snippets`) explicitly instructs the model to: use only the information in the provided snippets; not invent new functions, endpoints, or configuration values; reply with the exact string "I do not know based on the docs I have." if the snippets are insufficient; and briefly mention which files it relied on when it does answer. The naive-mode prompt has none of these constraints — it is just "You are a documentation assistant. Answer this developer question: {query}".

---

## 4. Experiments and Comparisons

Run the **same set of queries** in all three modes. Fill in the table with short notes.

You can reuse or adapt the queries from `dataset.py`.

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|------|---------------------------------|--------------------------------------|---------------------------|-------|
| Where is the auth token generated? | Harmful-ish — sounds confident, lists 4 generic architectures (OAuth IdP, custom backend, API keys, sessions), never mentions this project at all | Helpful but effortful — correctly surfaces the `## Token Generation` paragraph naming `generate_access_token`/`auth_utils.py`, plus two supporting paragraphs, but reader must scan and synthesize | Helpful — "The auth token is generated by the `generate_access_token` function in the `auth_utils.py` module." with `Source: AUTH.md` | Best 3-way contrast observed: naive is plausible-sounding fiction, retrieval is correct-but-raw, RAG is correct-and-readable |
| Which endpoint returns all users? | Harmful-ish — guesses `GET /users` or `GET /api/v1/users`, which are *not* this project's actual route (`GET /api/users`) | Helpful — top chunk is exactly `### GET /api/users` / "Returns a list of all users. Only accessible to admins." | Helpful — "The `GET /api/users` endpoint returns a list of all users." with `Source: API_REFERENCE.md` | Naive mode's guessed endpoint path is subtly wrong in a way a developer could easily copy-paste and ship |
| How do I connect to the database? | Neutral/harmful — generic, fluent tutorial on DB connections (Node/Python code samples, connection pooling) with zero mention of this project's actual `DATABASE_URL` variable or SQLite default | Helpful but redundant — returns 3 paragraphs, one of which is just the file's title/intro line, diluting the one paragraph that actually answers the question | Helpful — correctly synthesizes "`DATABASE_URL` environment variable... SQLite for local dev... PostgreSQL for production" from the retrieved paragraphs | Retrieval-only's inclusion of the low-value title/intro paragraph is a good example of "accurate but hard to interpret" |
| How does a client refresh an access token? | Harmful — writes a full generic OAuth2 refresh-token tutorial (HTTP request/response examples, rotation, pseudo-code) with zero connection to this project, despite the project *having* a real, simple answer (`POST /api/refresh`) | **Fails** — refuses with the guardrail message even though AUTH.md clearly documents this (`/api/refresh` in Client Workflow) | **Fails** — same refusal, since RAG never even calls the LLM when `retrieve()` returns `[]` | See Failure Case 2 below — this is the coverage-threshold's blind spot, not a document gap |
| Where is the apple generated? (nonsense/out-of-scope) | Harmful — invents an entire imagined "Snake game" context (`spawnApple()`, game loop, `Math.random()`) with no basis in the actual docs | Correctly refuses: "I don't have enough information to answer that." | Correctly refuses: "I don't have enough information to answer that." | See Failure Case 1 below — clean example of naive mode confidently hallucinating a scenario that doesn't exist in this project at all |

**What patterns did you notice?**  

- When does naive LLM look impressive but untrustworthy?  
- When is retrieval only clearly better?  
- When is RAG clearly better than both?

> Naive LLM is *most* impressive-looking exactly when it's most wrong — on the nonsense "apple" query it produces a detailed, structured, entirely fabricated Snake-game scenario, and on the real "which endpoint" query it guesses a wrong-but-plausible path (`GET /users`) that a developer could ship without noticing. It never signals uncertainty about *this specific codebase* because it was never shown it.
>
> Retrieval-only is never wrong about what it returns (it only echoes real file text), but it's "clearly better" than RAG only when you want to eyeball raw evidence yourself or don't trust a model to synthesize — it never wins on readability, and it sometimes pads results with low-value chunks (e.g. a file's title/intro line) that a synthesized answer would just omit.
>
> RAG is clearly better than both whenever retrieval actually surfaces the right paragraph(s): it keeps naive mode's fluent, direct phrasing while inheriting retrieval-only's groundedness and file citation. But RAG is *only as good as retrieve()* — when retrieval returns nothing (or the wrong thing), RAG can't rescue it, and unlike naive mode it will honestly refuse rather than guess.

---

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**  
For each one, say:

- What was the question?  
- What did the system do?  
- What should have happened instead?

> **Failure case 1 — Naive mode hallucinating a scenario ("Where is the apple generated?"):** the question is nonsense relative to this project (no "apple" concept exists anywhere in `docs/`). Naive LLM mode didn't say "I don't know" — it invented plausible programming context (a Snake-style game with `spawnApple()`/`createFood()`/a game loop) and confidently explained where "the apple" would be generated in that imagined system. It should have said it has no information connecting "apple" to this project, since it was never shown the docs at all and has no way to know they're irrelevant — but naive mode's prompt contains no instruction to express that uncertainty, so it defaults to being maximally "helpful" by inventing context.

> **Failure case 2 — Retrieval/RAG refusing on an answerable question ("How does a client refresh an access token?"):** AUTH.md's "Client Workflow" section documents this clearly (step 4: "Refresh the token when it expires by calling `/api/refresh`"), and the whole-document score for AUTH.md is 36 (100% query-term coverage). But the answer is split across two adjacent paragraphs — one mentions "access token", the other mentions "refresh"/`/api/refresh` — and neither single paragraph alone contains more than 2 of the 4 distinct query terms (client/access/token/refresh), which is exactly the >50% coverage threshold, causing every paragraph in the document to score 0. Both retrieval-only and RAG refused with "I don't have enough information to answer that," even though the document plainly contains the answer. The system should have retrieved the Client Workflow paragraph(s) and let RAG summarize the two-step process. This is a genuine gap caused by chunking at paragraph granularity combined with a per-chunk (rather than per-document) coverage requirement.

**When should DocuBot say "I do not know based on the docs I have"?**  
Give at least two specific situations.

> 1. When the question references a concept that literally does not exist anywhere in the docs corpus (the "apple" case) — no document or paragraph shares meaningful vocabulary with the query.
> 2. When the question is about this project but phrased with vocabulary so different from the docs that lexical matching can't bridge the gap (e.g. asking about "login flow" if the docs only ever say "Client Workflow" and "/api/login" without ever using the word "flow") — a true negative for this retrieval design, even though a human reading the docs would recognize the connection immediately.

**What guardrails did you implement?**  
Examples: refusal rules, thresholds, limits on snippets, safe defaults.

> - `MIN_QUERY_COVERAGE = 0.5` in `score_document`: a document or chunk scores 0 (is treated as irrelevant) unless more than half of the query's distinct, non-stopword tokens actually appear in it, regardless of how many times common words overlap.
> - `STOPWORDS` filtering in `tokenize()`, so words like "the"/"is"/"where" can never by themselves drive a relevance score or inflate coverage.
> - `retrieve()` returns `[]` whenever no document (or, after document selection, no chunk) clears the coverage bar, rather than falling back to weakly-matching results just to fill `top_k`.
> - `answer_retrieval_only`/`answer_rag` both check `if not snippets` and return the fixed guardrail string `"I don't have enough information to answer that."` without ever reaching the LLM in RAG mode — so a failed retrieval can't be papered over by the LLM inventing an answer.
> - The RAG system prompt separately instructs the LLM to refuse ("I do not know based on the docs I have.") if the snippets it *was* given turn out to be insufficient to answer confidently — a second layer of guardrail beyond the retrieval-level one.

---

## 6. Limitations and Future Improvements

**Current limitations**  
List at least three limitations of your DocuBot system.

1. Retrieval is restricted to a single best-scoring document per query (see Section 2), so it structurally cannot answer questions whose evidence spans two files.
2. The per-chunk coverage threshold can produce false-negative refusals when a real answer is split across adjacent paragraphs (Failure Case 2), even when the source document is unambiguously relevant.
3. Matching is purely lexical (stemmed bag-of-words) with no synonym or semantic understanding — a query using different-but-equivalent vocabulary from the docs (e.g. "sign in" vs. "login") will under-retrieve or refuse entirely.
4. Naive LLM mode has no awareness that project-specific docs even exist, so it cannot express calibrated uncertainty about this specific codebase — it will always answer from general knowledge as if that's what was asked.

**Future improvements**  
List two or three changes that would most improve reliability or usefulness.

1. Merge adjacent low-scoring-but-related paragraphs (or fall back to a slightly lower coverage threshold, or evaluate coverage across a small sliding window of consecutive paragraphs) before giving up, to fix cases like Failure Case 2 without reopening the door to "apple"-style false positives.
2. Allow retrieval to pull chunks from more than one document when multiple documents clear a high absolute score, rather than committing to a single winner up front.
3. Replace or augment lexical scoring with embedding-based semantic similarity to close the synonym/paraphrase gap, while keeping the coverage-style guardrail as a cheap first-pass filter.

---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**  
Think about wrong answers, missing information, or over trusting the LLM.

> Naive LLM mode's confidently-wrong endpoint guess (`GET /users` instead of the real `GET /api/users`) is the clearest concrete risk: a developer who trusts it and ships client code against the wrong path will get real runtime failures, and the failure mode (plausible-sounding, well-formatted, wrong) is exactly the kind that's easy to miss in a quick copy-paste. More broadly, any mode that answers with high confidence but low/no grounding (naive mode always; retrieval/RAG when the coverage threshold blocks a real answer) risks developers building on incorrect assumptions about auth, security-relevant config (`AUTH_SECRET_KEY`), or data access rules — mistakes in exactly the areas where correctness matters most.

**What instructions would you give real developers who want to use DocuBot safely?**  
Write 2 to 4 short bullet points.

- Prefer RAG mode over naive mode for any question about *this specific project* — naive mode is a general-knowledge chatbot with no idea this codebase exists, and its answers should be treated as generic tutorials, not project facts.
- Treat a "I don't have enough information to answer that" response as "check the docs yourself," not "the docs don't cover this" — the retrieval design can produce false-negative refusals (Failure Case 2) even when the docs do contain the answer.
- Cross-check RAG's cited file (`Source: AUTH.md`, etc.) against the actual file before trusting a security- or config-relevant answer (secrets, auth flow, permissions) — don't treat the citation alone as proof of correctness.
- If precise wording matters (e.g. asking about "login" vs. the docs' "authenticate"), try rephrasing the query using vocabulary closer to what's likely in the docs — this system's matching is lexical, not semantic.
