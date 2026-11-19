# Folio — speaker guide

**Audience:** data / analytics engineers who know tables and are nervous about PDFs + AI spend.
**Length:** 30 min + 5 Q&A.
**Surface:** Streamlit `make dashboard-bq` (pages 1 → 14, sidebar order = speaker order). Backup: BigQuery Studio + [`presentation_queries.sql`](presentation_queries.sql) (query ids map to page numbers).

---

## The problem, in four sentences (say this first, verbatim if you like)

1. A credit analyst must answer **one question**: *“Is this borrower heading toward a covenant breach — and which documents prove it?”*
2. The evidence is **not in a table**. It is spread over invoices, loan agreements, credit memos, analyst notes, earnings calls and SEC filings.
3. Naive AI (“put every PDF in a vector database”) is **noisy, expensive and unauditable**: it embeds blank scans and PII, returns other borrowers’ boilerplate, and cannot cite a file.
4. **Folio’s answer:** treat documents like data — Bronze → Silver → Gold — and only then spend AI tokens, with tests, a cost ledger and lineage.

**One-sentence pitch:** *Medallion governance + context engineering beats “dump PDFs into a vector DB.”*

---

## Agenda (5 acts, 14 pages)

| Act | Pages | Question it answers |
|---|---|---|
| **I Problem** | 1 problem · 2 the case · 3 approach | What are we solving, for whom, with what pattern? |
| **II Ingest** | 4 Bronze · 5 discovery · 6 Silver | How do files arrive, and which are allowed in? |
| **III Structure** | 7 Gold · 8 Embeddings · 9 Taxonomy | How do we turn text into something queryable? |
| **IV Use it** | 10 Search · 11 Extraction | Does it actually find and read the right documents? |
| **V Trust** | 12 Evals · 13 Cost & lineage · 14 Wrap-up | Can we measure it, afford it and audit it? |

Appendix page **A** is the SQL pack (live click-through in BigQuery Studio).

---

## Data you can quote (current build)

| Fact | Value |
|---|---|
| Files / borrowers / formats | 100 / 12 / 7 |
| Meridian (ACC-8847) files | 16 (15 usable, 1 quarantined for PII) |
| Silver | 96 ready · 4 quarantined (2 parse failed, 1 low quality, 1 PII) |
| Gold tiers | 3 high · 13 medium · 80 low |
| Chunks embedded | 102 (text-embedding-005, 768 dims) |
| Search top 10 for *“Which borrower is at risk of default?”* | raw: 5 other-borrower results · filtered: 0 |
| Regex vs extract() on 17 docs | 14 agree · 2 regex false alarms · 1 regex missed |
| Classify eval | 87% accuracy (13/15); misses 10Q-Q3-MDA and EARN-Q3-2025 |
| AI spend (est.) | ≈ $0.025 total; classify is the largest line |

Re-check after any rebuild: `make dashboard-warm` then page 14.

---

## Page-by-page script

Each page: **Goal → Say → Chart (axes · read · so what) → Transition.**

### 1 · The problem (2 min)
- **Goal:** the room can repeat the analyst question and the five failure modes.
- **Say:** the four-sentence problem above; point at the three metrics (100 files, 12 borrowers, 7 formats).
- **Five failure modes:** scattered signal · noise · unusable files · tokens billed per call · answers without proof.
- **Transition:** “Let’s meet the borrower.”

### 2 · The case: Meridian (2 min)
- **Goal:** make the needle-in-haystack concrete.
- **Chart 1 — files per borrower**
  - *Axes:* Y borrower · X number of files.
  - *Read:* red = Meridian (16), grey = healthy borrowers (7–9 each).
  - *So what:* a search across everything returns plenty of other people’s paperwork.
- **Table — Meridian’s case file:** 16 files in 6 formats, one already marked `quarantine_pii_review`.
- **Transition:** “How do we get from this folder to an answer without trusting everything blindly?”

### 3 · The approach (2 min)
- **Goal:** one picture of the pipeline and the package.
- **Say:** four cards (Bronze / Silver / Gold / Context). Two kinds of Gold: **rule-based** (free, literal) and **AI-based** (semantic, billed). “The talk is *and*, not *replace*.”
- **Table:** package capability ↔ Folio model ↔ plain meaning. Don’t read it all; promise to show each.
- **Transition:** “First: how do files even get in?”

### 4 · Bronze: catalog, not meaning (2 min)
- **Goal:** Bronze = provenance only, and *where the bytes live* is a decision.
- **Say:** URI + `content_sha256` + type, nothing interpreted. **Zero-copy vs physical copy** first: metadata-only Bronze leaves the file in the bucket (less storage, smaller attack surface; re-parse hits the source); physical copy keeps a snapshot (audit trail; duplicate storage). This demo copies PDFs into git and `dbt seed` (Cloud-friendly); production leans metadata-only.
- **Table:** point at `uri`, `content_sha256`, `bronze_layer`.
- **Transition:** “Either way, someone has to fill that catalog. How do new files get noticed?”

### 5 · Discovery: events vs crawler (2 min)
- **Goal:** show the production ingestion decision (demo uses seeds).
- **Read the image left → right:** event-driven = upload fires an event → queue → worker → catalog (instant, pay per change). Crawler = scheduled list + hash diff (complete, chatty, late).
- **Say:** crawl once → events day to day → periodic re-crawl for dark data.
- **Transition:** “Whatever way they arrive, Bronze trusts everything. Silver doesn’t.”

### 6 · Silver: the gate (3 min) — most important page of Act II
- **Goal:** answer “what is the silver gate?”
- **Say:** *it is a column, not a table*: `silver_status` in `silver_document_bodies`, a CASE where the first rule wins (parse failed → quality < 0.4 → restricted PII → ready). Downstream models read the view `silver_ready_documents`.
- **Chart 1 — one square per file (waffle)**
  - *Axes:* none — 100 squares, one per file; hover shows the file. Sorted by status, green first.
  - *Read:* green = passed (96); each other colour = a different rule that stopped the file (2 parse failed, 1 low quality, 1 PII).
  - *So what:* the gate is rare on purpose; the four red/amber/purple squares never reach Gold, never get embedded, never cost tokens.
- **Chart 2 — quality score histogram with the 0.4 rule**
  - *Axes:* X parse quality (bins of 0.1) · Y number of files · colour = verdict.
  - *Read:* left of the dashed line fails rule 2. The purple file is on the right (good quality) but blocked by rule 3 — it contains an SSN.
  - *So what:* the gate is not just a quality filter; sensitivity is a separate reason to stop a file.
- **Table — quarantined files and why.**
- **Anti-pattern cards:** Bronze→Vector embeds the blank scan, garbled fax **and the SSN memo**. *“Vectors without Silver are an ungoverned second copy.”*
- **Transition:** “Now that the inputs are clean, what can plain SQL tell us?”

### 7 · Gold: rule-based flags (3 min)
- **Goal:** explain what “risk flags” mean — they are word matches, **not** a credit score.
- **Say:** three word lists (past due · covenant · liquidity). Tier: **high** = covenant *and* liquidity · **medium** = any one · **low** = none.
- **Chart 1 — documents per borrower, split by tier**
  - *Axes:* Y all 12 borrowers · X number of documents (each counted once) · colour = tier (red high, amber medium, light grey low).
  - *Read:* the coloured part of a bar is what the rules consider risky.
  - *So what:* Meridian is mostly red/amber; ten borrowers are all grey. Two bars (Summit Rail, BrightPeak) show **one amber document each** — **plant the seed**: “remember these two.”
- **Chart 2 — heatmap: Meridian documents × the three word lists**
  - *Axes:* Y one row per Meridian document with its tier · X past due / covenant / liquidity.
  - *Read:* red cell = that word list matched. Covenant + liquidity both red = high; one red = medium; none = low.
  - *So what:* this is the whole “risk” logic — three yes/no questions, no score. Easy to audit, but it only sees words.
- **Metrics above the charts:** 3 high · 13 medium · 80 low (use them to explain tiers before the charts).
- **Transition:** “Rules match words. Can we match meaning?”

### 8 · Embeddings: meaning as numbers (3 min)
- **Goal:** demystify the embedding.
- **Say:** a passage becomes 768 numbers; similar meaning ⇒ nearby numbers. Picture a map of dots.
- **Chart — nearest neighbours of one chunk**
  - *Axes:* Y chunk id · X cosine similarity to the anchor (1.0 = identical) · colour = doc type.
  - *Read:* anchor is a past-due invoice (MER-X01); top neighbours are other invoices, covenant memos appear later.
  - *So what:* that is “meaning”, measured — without a keyword list.
- **Mention:** `content_hash` (re-embed only if text changes), fingerprint (model change ⇒ rebuild).
- **Transition:** “To filter by meaning we need labels.”

### 9 · Taxonomy: classify (2 min)
- **Goal:** closed label list = governable filter.
- **Say:** five labels, one per chunk. “The label set is a product decision.”
- **Chart — chunks per label:** Y label · X chunks · red = risk labels, grey = routine/disclosure. Risk labels are a small slice from one borrower — a filter on them removes most noise.
- **Table:** one example chunk per label.
- **Transition:** “Let’s prove the filter helps.”

### 10 · Search: raw vs filtered (3 min) — the “aha”
- **Question on screen:** *“Which borrower is at risk of default?”*
- **Chart — who shows up in the top 10?**
  - *Axes:* X search variant (A raw cosine · B cosine + label filter) · Y results out of 10 · colour = Meridian (green) vs other borrowers (red).
  - *Read:* A has 5 red results; B has none.
  - *So what:* same model, same vectors; one `WHERE classification in (…)` buys precision.
- **Tables:** point at the `account_key` column — any value other than ACC-8847 is noise.
- **Transition:** “Search finds passages. Can the model read a whole document and fill in a record?”

### 11 · Extraction: regex vs extract() (3 min) — pays off page 7’s seed
- **Say:** `extract()` returns typed fields **and a verbatim quote**; `grounded` fails the build if the quote isn’t in the source. Cost gate: only Meridian + regex-flagged docs (17 of 96).
- **Chart — agreement of the two methods on 17 docs**
  - *Axes:* Y verdict · X documents.
  - *Read:* green = agree (14); red = regex false alarm (2); amber = regex missed it (1).
  - *So what:* rules are mostly right, but the misses hurt — use rules for triage, model for subtle wording.
- **The three disagreements:**
  - **CFA-2024-11** (Summit Rail): regex sees “covenant” → medium; it’s a comfortable-headroom disclosure.
  - **EARN-Q2-BP** (BrightPeak): regex sees “liquidity” in a routine call; model says none.
  - **INV-4412** (Meridian): “cash timing pressure tied to delayed receivables” — no keyword, regex says low; model catches it.
- **Transition:** “The model disagreed with regex. Who checks the model?”

### 12 · Evals: is the AI right? (3 min)
- **Say:** a golden set (15 Meridian docs with the human label) is scored with `eval()` — like a unit test. Define **precision** (when it says X, is it right?) and **recall** (of the true X, how many found?).
- **Chart — precision and recall per label**
  - *Axes:* Y label · X score 0–1 · blue precision, amber recall.
  - *Read:* full bar = perfect; **“n/a” = undefined** (public_disclosure was never predicted, so precision is n/a and recall is 0.00).
  - *So what:* accuracy 87%, and the misses teach us something.
- **Misses:** 10Q-Q3-MDA (filing *is* about covenants) and EARN-Q3-2025 (discusses both). Fix is a taxonomy/prompt decision → rerun → metrics move → CI-able.
- **Transition:** “What did all this cost, and can we trace an answer back?”

### 13 · Cost & lineage (2 min)
- **Chart — estimated tokens per AI function:** Y function · X tokens · green = started *and* completed (a red bar = orphaned run). **classify is the biggest line** (prompt resent with every chunk); embed is the smallest (incremental on `content_hash`).
- **Gates:** `max_batch_rows=5000`, `max_est_tokens=2,000,000` — a runaway job fails before it bills. AI is opt-in (`ai_functions_enabled`).
- **Chart — lineage status:** `fully_promoted` vs `quarantined`; every row keeps `content_sha256` + `citation_url`. Use the drill-down to show a hash.
- **Transition:** “Let’s close the loop on the analyst’s question.”

### 14 · Wrap-up (2 min)
- **Chart — document funnel:** 100 Bronze → 96 Silver ready → 96 Gold → 16 flagged. AI spend happens on stage 2, not stage 1.
- **Answer the opening question** (the text on screen): Meridian — usable docs, past-due / covenant / liquidity counts, leverage up to 3.75x — with quotes, hashes, and a measured error rate.
- **Three sound bites:** (1) vectors without Silver are an ungoverned second copy · (2) rules are cheap and explainable, models understand meaning — use both and measure both · (3) treat AI outputs like dbt models: tests, evals, ledger, lineage.

### A · SQL pack (optional, live)
Pick a query, read it aloud, run it. Same SQL as `presentation_queries.sql`; the number in each query id equals the page number.

---

## Timing cheat sheet

| Min | Pages | Do |
|---|---|---|
| 0–6 | 1–3 | Problem, case, approach |
| 6–15 | 4–6 | Ingest (Bronze → discovery → Silver); spend most time on the Silver gate |
| 15–23 | 7–9 | Gold flags → embeddings → taxonomy |
| 23–29 | 10–11 | Search aha + regex vs extract |
| 29–34 | 12–14 | Evals, cost/lineage, wrap-up |
| 34–39 | — | Q&A |

If you need 20 minutes: skip page 5, say page 4 in one sentence, merge 8+9.

---

## Decisions worth defending

1. **Seeds vs zero-copy** — demo copies PDFs + `dbt seed` for one-click Cloud; production uses metadata-only Bronze. Frame as *presentation fidelity*, show the URI/sha256 hook.
2. **Silver before vectors** — quality + sensitivity + quarantine first.
3. **Rules *and* AI** — Gold regex vs AI path; show both, with the disagreements.
4. **Taxonomy is a product decision** — a bad label set quietly filters the right answer away; evals make it testable.
5. **Cost gates are architecture** — `ai_functions_enabled: false` by default, `guard_batch` ceilings, `allow_full_reembed: false`, `bq_thinking_budget: 0`, `gov_ai_spend` ledger.
6. **Lineage is the citation story** — `content_sha256` from Bronze → Silver → chunks.
7. **Noise is intentional** — other borrowers’ boilerplate makes raw search fail visibly; if search only returned Meridian the demo would be too clean.
8. **Warehouse-native AI** — same dbt project on BigQuery (Gemini / `AI.*`) or Redshift (Bedrock UDFs); one provider per target, not mixed in one build.

---

## Slide-ready contrasts

```text
Bronze → Vector shortcut          Folio path
─────────────────────────         ──────────────────────────
Parse? maybe                      Docling → Silver gates
Sensitivity? later                Labels before embed
Cost? unbounded fan-out           guard_batch + opt-in AI
Cite file? weak                   sha256 through chunks
```

```text
Method                     Strength              Blind spot
─────────────────────      ──────────────────    ────────────────────
regex flags (Gold)         Free, explainable     Matches words, not meaning
vector search              Recall by meaning     Boilerplate pollution
+ classification filter    Precision             Taxonomy design debt
extract() + grounded       Typed + cited         Costs tokens; needs evals
```

---

## Questions to pre-answer

| Likely question | Short answer |
|---|---|
| What is the silver gate? | A CASE expression producing `silver_status`; downstream reads `silver_ready_documents` |
| Why not only a vector DB? | Lose warehouse lineage, tests, cost controls and joins |
| Why classify if embeddings are semantic? | Embed = recall; a closed taxonomy = precision for this question class |
| Why did regex flag Summit Rail? | It matches the word “covenant” — the doc says headroom is comfortable (page 11) |
| Why is precision blank for public_disclosure? | The model never predicted that label on the golden docs |
| Who owns sensitivity labels? | Silver stewardship — same as PII columns on tables |
| How do you RTBF a PDF? | Find `content_sha256` / `doc_id` in lineage; purge object + downstream chunks/embeddings |
| Can I mix Bedrock and Gemini? | Not in one build; use two targets (BigQuery → Gemini, Redshift → Bedrock) |
| What breaks first in prod? | Bad parses, prompt drift, full-refresh re-embed bills, taxonomy mismatch |

---

## Props / links to open beforehand

1. GitHub: `https://github.com/weslleylc/folio`
2. Article: [Beyond Tables…](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835)
3. Package: [`dbt_context_engineering`](https://github.com/dbt-labs/dbt-context-engineering)
4. Streamlit: `make dashboard-warm && make dashboard-bq` → http://localhost:8505
5. SQL backup: [`presentation_queries.sql`](presentation_queries.sql)
6. Optional: `models/silver/silver_document_bodies.sql` open in the IDE for page 6
