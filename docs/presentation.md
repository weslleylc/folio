# Folio — speaker guide (demo / talk)

Audience: data / analytics engineers who know tables, are nervous about PDFs + AI spend.  
Tone: show the **problem**, the **governance moves**, then the **AI payoff** — not “we embedded everything.”

Suggested length: **20–25 min** + 5 min Q&A.

---

## One-sentence pitch

> When the signal for one credit account lives across invoices, covenants, memos, and filings, medallion governance + context engineering beats “dump PDFs into a vector DB.”

---

## Narrative arc (slide order)

| # | Beat | Why it lands |
|---|---|---|
| 1 | Meridian story | Concrete: ACC-8847 is stressed; fragments are scattered; noise accounts exist |
| 2 | Unstructured medallion | Bronze / Silver / Gold is familiar — applied to PDFs, not only tables |
| 3 | Zero-copy vs physical copy | Architecture decision the room will argue about — own it |
| 4 | Bronze → Vector shortcut | The anti-pattern; Silver is the spend + quality gate |
| 5 | Join / regex ceiling | Gold rollup + timeline work — then show what they **cannot** do |
| 6 | Chunk → embed → classify → search | Context engineering as ordinary dbt models |
| 7 | Classification buys precision | Same query, raw cosine vs taxonomy filter |
| 8 | Cost + lineage governance | Gates, `ai_run_log`, RTBF / sha256 — AI is a governed consumer |
| 9 | Close | Demo choices vs production choices |

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

### B. Silver — the gate

```sql
select doc_id, quality_score, sensitivity_label, silver_status
from silver_document_bodies
order by quality_score;
```

**Say:** “Quarantine before vectors. Low quality and failed parses never get an embedding bill.”

### C. Gold — structured ceiling

```sql
select * from gold_account_risk_rollup
order by max_risk_tier desc, covenant_docs desc;
```

Meridian should stand out (past-due + covenant + liquidity).

Then timeline (compile/run `analyses/meridian_narrative.sql`):

**Say:** “Joins reconstruct a timeline. They don’t answer: *which passage talks about covenant headroom across mixed PDFs?*”

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
