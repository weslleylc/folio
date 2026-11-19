# Folio — speaker guide (demo / talk)

Audience: data / analytics engineers who know tables, are nervous about PDFs + AI spend.  
Tone: show the **problem**, the **governance moves**, then the **AI payoff** — not “we embedded everything.”

Suggested length: **25–30 min** + 5 min Q&A.  
Live UI: Streamlit `make dashboard-bq` (pages **0 → 9**) or BigQuery Studio + `docs/presentation_queries.sql`.

---

## One-sentence pitch

> When the signal for one credit account lives across invoices, covenants, memos, and filings, medallion governance + context engineering beats “dump PDFs into a vector DB.”

---

## Opening — the ingestion problem (say this first)

Financial document estates break “table-first” habits:

1. **Signal is scattered** — past-due on an invoice, covenant headroom in a facility PDF, DSO on an earnings call.
2. **Noise dominates** — healthy accounts drown Meridian in naive keyword / vector search.
3. **Parses fail** — blank scans and OCR garbage must be quarantined before any embedding bill.
4. **AI without gates** — embedding Bronze (or everything Silver) is an ungoverned secondary store.
5. **No citation** — an answer without URI / `content_sha256` / evidence quote is a demo, not audit-ready.

**Folio answer:** Bronze catalog → Silver gate → Gold regex facts **and** package AI (`chunk` / `embed` / `classify` / `extract` / `search`) under `guard_batch` + `eval` / `grounded`.

---

## Narrative arc (slide / Streamlit order)

| # | Beat | Streamlit page | Why it lands |
|---|---|---|---|
| 0 | Ingestion problem | `0 · The problem` | Frame why PDFs hurt credit analytics |
| 0b | What Folio proves | `0b · What Folio proves` | Two Gold paths: regex **and** AI |
| 1 | Meridian story | Overview / Gold | ACC-8847 stressed; ~100-doc corpus with noise |
| 2 | Unstructured medallion | D1–D3 | Familiar layers on unfamiliar data |
| 3 | Zero-copy vs physical copy | D1 | Own the Cloud demo choice (seeds) |
| 4 | Bronze → Vector anti-pattern | D3 | Silver must show quarantine bars |
| 5 | Join / regex ceiling | `1 · Gold rollup` | Explain flags/tiers didactically |
| 6 | Embeddings mart | `6 · Embeddings mart` | What a vector row *is* |
| 7 | Classify + search | `3` / `4` | Precision unlock |
| 8 | Typed extract | `7 · Typed extraction` | Package `extract()` + evidence |
| 9 | Evals | `8 · Evals & package` | `eval` / `grounded` like unit tests |
| 10 | Cost + lineage | `5` | Gates + sha256 |
| 11 | SQL pack | `9 · SQL talk pack` | Live Studio click-through |

---

## Live demo script (BigQuery / dbt Cloud)

Run order. Keep SQL short; talk over results.

### A. Bronze — provenance, not interpretation

```sql
select doc_id, doc_type, account_id, uri, content_sha256, bronze_layer
from bronze_document_catalog
order by effective_date;
```

**Say:** “No NLP here. Hash + URI + source system. That’s the contract.”

**Zero-copy aside (30–45s):**  
- *This demo:* physical-copy PDFs in git + **seeds** into BQ (easy for Cloud).  
- *Production pattern:* metadata-only Bronze — binaries stay in GCS/S3; warehouse keeps URI + sha256; selective snapshot only when you must.  
- *Punchline:* zero-copy is about **not duplicating the source of truth**; Silver/embeddings are still derived copies by design.

### B. Silver — the gate (chart must show quarantine)

```sql
select silver_status, count(*) as docs
from silver_document_bodies
group by 1;

select doc_id, quality_score, parse_status, sensitivity_label, silver_status
from silver_document_bodies
where silver_status != 'silver_ready'
order by quality_score;
```

**How to read `silver_status` (say this out loud):**
- `silver_ready` — parse ok **and** quality ≥ 0.4 → allowed into Gold / chunk / embed
- `quarantine_low_quality` — body too thin / garbled (quality &lt; 0.4)
- `quarantine_parse_failed` — extractor marked `failed`

**Say:** “If every bar is ready, Silver looks fake. We plant a few bad scans on purpose — those never get an embedding bill.”  
**Note:** `sensitivity_label` (e.g. `restricted_pii`) is a governance tag; it is **not** the same as quarantine.

### C. Gold — what “risks” actually are

```sql
-- Per document: three boolean flags from SQL regex on Silver markdown
select doc_id, title,
       flag_past_due, flag_covenant_language, flag_liquidity_language,
       risk_signal_tier
from gold_document_facts
where account_id = 'ACC-8847'
order by risk_signal_tier desc;

-- Per account: count of docs that tripped each flag
select * from gold_account_risk_rollup
order by max_risk_tier desc, covenant_docs desc;
```

**How to read Gold “risks” (not a credit score):**
| Flag | Text match (demo) |
|---|---|
| `flag_past_due` | past due / overdue / credit hold |
| `flag_covenant_language` | covenant / leverage ratio / event of default |
| `flag_liquidity_language` | working capital / DSO / liquidity |

**Tier:** `high` = covenant **and** liquidity in the **same** doc · `medium` = any one flag · `low` = none.

**Say:** “Meridian’s story PDFs trip these phrases on purpose; noise accounts stay clean so the rollup chart is readable. Joins reconstruct a timeline — they still don’t answer *which passage* talks about covenant headroom across mixed PDFs.”

Then timeline (compile/run `analyses/meridian_narrative.sql`).

### D. Context engineering — meaning + filter

After `dbt build --vars '{"ai_functions_enabled": true}'`:

```sql
select demo, classification, left(text, 120) as snippet, score
from search
order by demo, score desc;
```

**Say:**  
1. **Raw** cosine recalls related text — often boilerplate.  
2. **Classified** filter (`covenant_or_credit_risk` / `liquidity_or_working_capital`) is the precision unlock — same lesson as Jaffle logistics.

Point at taxonomy in `macros/prompts/folio_content_type.sql` (closed enum = governable labels).

### D2. Embeddings mart — show the shape

```sql
select chunk_id, account_id, embedding_dimension, model_version,
       substr(chunk_text, 1, 100) as preview
from documents_embed
where account_id = 'ACC-8847'
limit 10;
```

**Say:** “An embedding is a derived float array under a pinned model. `content_hash` decides refresh; fingerprint decides full re-embed.”

### D3. Typed extraction — package `extract()`

```sql
select doc_id, primary_signal, leverage_mention, usd_amount_mention,
       substr(evidence, 1, 120) as evidence
from documents_extract_flat
order by primary_signal;
```

**Say:** “Regex Gold is free and brittle. `extract()` returns typed fields **plus** a verbatim evidence quote — `grounded` fails hallucinated citations in CI.”

### D4. Evals — score the taxonomy

```sql
select * from gov_classify_eval order by metric, label;

select doc_id, expected_label, predicted_label, is_correct
from gov_classify_eval_pairs
order by is_correct, doc_id;
```

**Say:** “Prompt/schema changes are product changes. `eval()` gives accuracy/precision/recall against a golden Meridian set — same discipline as a dbt test.”

### E. Governance — cost + lineage

```sql
select function_name, model_name, row_count, est_tokens, est_cost_usd, cost_source
from gov_ai_spend;

select doc_id, content_sha256, chunk_count, lineage_status
from gov_document_lineage
where account_id = 'ACC-8847';
```

**Say:** “Spend is logged and gated (`ai_functions_enabled`, `guard_batch` ceilings). Lineage carries `content_sha256` so a Gold answer can cite a file hash — RTBF / purge has a drill path.”

Optional: Streamlit dashboard locally if the room is DuckDB-friendly; otherwise BigQuery Studio on `gov_*`.

---

## Decisions worth defending (talking points)

### 1. Seeds vs zero-copy (this talk)

| Choice | Folio demo | Production lean |
|---|---|---|
| Bronze binaries | In-repo PDFs | Object store; catalog only |
| Land text in WH | `dbt seed` markdown | Pipeline → table or Object Table |
| Why seeds here | One `dbt build` on Cloud; no GCS setup in the talk | Ops reality at scale |

**Tip:** Don’t apologize for seeds — frame as *presentation fidelity*. Show the URI/sha256 columns as the hook to zero-copy later.

### 2. Silver before vectors

Embedding Bronze is cheap to start and expensive to trust. Quality + sensitivity + quarantine first.  
**Sound bite:** “Vectors without Silver are an ungoverned secondary store.”

### 3. Deterministic Gold vs AI Gold

| Path | What | Cost |
|---|---|---|
| Regex / SQL facts | `gold_document_facts`, rollup | Free, explainable, brittle |
| Context engineering | chunk → embed → classify → search | Billed, semantic, needs gates |

Show **both**. The talk is “and,” not “replace SQL with RAG.”

### 4. Classification taxonomy is a product decision

Five labels in `folio_content_type` — designed for *this* credit story.  
**Tip:** Say out loud that a bad taxonomy quietly filters the right answer away. Governance of prompts/schemas matters as much as model choice.

### 5. Cost gates are part of the architecture

- `ai_functions_enabled: false` by default  
- `max_batch_rows` / `max_est_tokens` circuit breaker  
- `bq_thinking_budget: 0` (don’t pay Gemini thinking for classify)  
- `allow_full_reembed: false`  
- `cost_per_1k_tokens` + `gov_ai_spend` for a visible ledger  

**Tip:** Flip AI **on** mid-talk so the room sees the gate is real, not slideware.

### 6. Lineage is the citation story

`content_sha256` from Bronze → Silver → chunk metadata.  
Agent answer without hash/URI is a demo; with hash it’s an audit trail.

### 7. Noise documents are intentional

BrightPeak / Summit Rail docs exist so naive search isn’t trivial.  
**Tip:** If search only ever returns Meridian, the demo is too clean — mention the noise.

### 8. Warehouse-native AI (BigQuery `AI.*`)

Same dbt project, DuckDB locally (stand-ins) vs BigQuery (real spend).  
**Tip:** “Portable patterns, engine-specific functions” — package dispatch, not a sidecar vector DB for the happy path.

---

## Slide-ready contrasts (use as diagrams)

```text
Physical copy          Metadata-only (zero-copy lean)
─────────────────      ──────────────────────────────
PDF bytes in lake      PDF bytes stay in bucket
Catalog + optional     Catalog: uri + sha256 + mime
  binary snapshot      Snapshot only when required
Demo / regulated       Default for large estates
  freeze
```

```text
Bronze → Vector shortcut          Folio path
─────────────────────────         ──────────────────────────
Parse? maybe                      Docling → Silver gates
Sensitivity? later                Labels before embed
Cost? unbounded fan-out           guard_batch + opt-in AI
Cite file? weak                   sha256 through chunks
```

```text
Query style                Strength              Blind spot
─────────────────────      ──────────────────    ────────────────────
account_id join + regex    Timeline, rollups     Wording / meaning
vector search              Recall by meaning     Boilerplate pollution
+ classification filter    Precision             Taxonomy design debt
```

---

## Questions you should pre-answer

| Likely question | Short answer |
|---|---|
| Why not only a vector DB? | Lose warehouse lineage, tests, cost controls, joins to account dims |
| Why classify if embed is semantic? | Embed = recall; closed taxonomy = precision for *this* question class |
| Who owns sensitivity labels? | Silver stewardship — same as PII columns on tables |
| How do you RTBF a PDF? | Find `content_sha256` / `doc_id` in lineage; purge object + downstream chunks/embeddings |
| What breaks first in prod? | Bad parses, prompt drift, full-refresh re-embed bills, taxonomy mismatch |

---

## Timing cheat sheet

| Min | Do |
|---|---|
| 0–3 | Meridian story + “signal is scattered” |
| 3–7 | Medallion walk (Bronze → Silver → Gold SQL) |
| 7–10 | Zero-copy vs copy + why seeds for *this* talk |
| 10–14 | Join ceiling → turn on AI / show search raw vs classified |
| 14–20 | Cost gates + lineage + taxonomy as decisions |
| 20–25 | Prod checklist + Q&A |

---

## Props / links to open beforehand

1. GitHub: `https://github.com/weslleylc/folio`  
2. Article: [Beyond Tables…](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835)  
3. Package: [`dbt_context_engineering`](https://github.com/dbt-labs/dbt-context-engineering)  
4. Ready SQL: [`presentation_queries.sql`](presentation_queries.sql) (BigQuery, `dbt_wcaldas`)  
5. Charts: **`make dashboard-bq`** — Streamlit over BigQuery ([`visualizations.md`](visualizations.md))  
6. SQL backup: [`presentation_queries.sql`](presentation_queries.sql)  
7. Optional: `folio_content_type` macro open in IDE  

---

## Queries + viz (Cloud talk)

**Streamlit + BigQuery** is the presentation surface (`make dashboard-bq`).

| Page | Beat |
|---|---|
| 1 | Gold rollup — Meridian spike |
| 2 | Silver gate |
| 3 | Search raw vs classified |
| 4 | Taxonomy |
| 5 | Cost + lineage |

```bash
gcloud auth application-default login
make dashboard-bq   # http://localhost:8501
```
