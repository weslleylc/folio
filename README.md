# Folio — context engineering over financial documents

Demo project that turns **unstructured financial PDFs** into a governed, searchable knowledge base:

1. **Medallion for unstructured data** (Bronze → Silver → Gold) following [Beyond Tables: Medallion for Unstructured Data Governance](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835)
2. **Docling** to parse PDFs into Silver markdown + metadata
3. **[`dbt_context_engineering`](https://github.com/dbt-labs/dbt-context-engineering)** for chunk → embed → classify → knowledge_base → search

Use it to demonstrate how context engineering works when the source of truth is not a clean table — invoices, credit amendments, earnings excerpts, MD&A, analyst notes — and the signal for one account is scattered across files.

## The story (Meridian Industrial)

**ACC-8847 / Meridian Industrial Corp** shows rising working-capital stress and thin covenant headroom in Q3–Q4 2025. Fragments live in different document types and source systems; unrelated accounts add noise.

| Doc ID | Type | Signal |
|---|---|---|
| INV-4401, INV-4412 | Invoices | Past-due / partial pay, AP stretch |
| CFA-2025-03 | Credit facility | Leverage covenant amended to 3.75x |
| MEMO-CC-991 | Credit memo | Committee risk review + monitoring |
| EARN-Q3-2025 | Earnings call | CFO on DSO / limited headroom |
| 10Q-Q3-MDA | SEC MD&A | Liquidity disclosure |
| NOTE-ANL-77 | Analyst note | Covenant watch |

## Quick start (DuckDB)

```bash
cd /Users/weslleylc/Documents/Projects/Blue Orange/folio

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1) Land sample PDFs in Bronze
python scripts/generate_sample_pdfs.py

# 2) Docling Bronze → Silver (+ refresh dbt seeds)
python scripts/extract_with_docling.py

# 3) dbt profile
mkdir -p ~/.dbt
# merge profiles.yml.example into ~/.dbt/profiles.yml as profile `folio`

dbt deps
dbt build
```

`ai_functions_enabled` defaults to **false**, so a plain `dbt build` never bills for embed/classify. On DuckDB the AI models are disabled; hashed chunks + Gold SQL still build.

### Optional: real AI layer (BigQuery / Snowflake / Databricks)

```bash
dbt build --vars '{"ai_functions_enabled": true}'
```

Cost gates in [`vars.yml`](vars.yml) keep a demo-sized run cheap and trip early on oversized batches:

| Var | Demo default | Role |
|---|---|---|
| `ai_functions_enabled` | `false` | Master spend gate |
| `max_batch_rows` / `max_est_tokens` | `500` / `200000` | `guard_batch` circuit breaker |
| `max_output_tokens` / `bq_thinking_budget` | `1024` / `0` | Cap Gemini output / disable thinking |
| `cost_per_1k_tokens` | `0.00015` | Populate `ai_run_log.est_cost` |
| `allow_full_reembed` | `false` | Block accidental full re-bill |

### dbt Cloud + BigQuery

Step-by-step: **[docs/dbt-cloud-bigquery.md](docs/dbt-cloud-bigquery.md)** (Vertex API, service account, Cloud connection, AI job vars). SQL is portable via `macros/cross_db.sql`; local DuckDB still works.

## Layout

```
bronze/documents/     # raw PDFs (physical-copy Bronze for the demo)
silver/extracted/     # Docling markdown + JSON metadata
seeds/                # catalog + bodies loaded into the warehouse
models/
  bronze/             # document catalog (provenance, SHA-256)
  silver/             # parsed bodies, quality + sensitivity gates
  gold/               # structured facts + account risk rollup
  context/            # chunk / hash (deterministic)
  context/ai/         # embed, classify, knowledge_base, search (gated)
analyses/             # Meridian narrative (join/regex ceiling)
docs/architecture.md  # medallion ↔ context-engineering map
docs/dbt-cloud-bigquery.md  # dbt Cloud + BigQuery deploy
docs/presentation.md  # speaker guide / demo beats
```

## Governance dashboard

Streamlit app over DuckDB for the metrics the medallion article cares about — **token/cost spend**, quarantine rates, sensitivity labels, lineage / RTBF surface, classification mix:

```bash
pip install streamlit pandas   # or: pip install -r requirements.txt
dbt build --vars '{"ai_functions_enabled": true}'   # populates ai_run_log + classify
make dashboard   # → streamlit run dashboard/app.py
```

Marts under `models/gold/governance/`:

| Model | Purpose |
|---|---|
| `gov_ai_spend` / `gov_ai_spend_daily` | Tokens & USD from `ai_run_log` (+ `ref_ai_pricing` when `est_cost` is null) |
| `gov_medallion_health` | Bronze/Silver/Gold coverage, quality, freshness, AI totals |
| `gov_document_lineage` | Doc → sha256 → chunks (purge / RTBF drill) |
| `gov_sensitivity_breakdown` | Privacy label distribution |
| `gov_classification_breakdown` | Retrieval taxonomy mix (AI layer) |

## Demo flow

1. **Bronze catalog** — `select * from bronze_document_catalog`
2. **Silver gate** — `select doc_id, quality_score, sensitivity_label, silver_status from silver_document_bodies`
3. **Gold facts** — `select * from gold_account_risk_rollup` (Meridian stands out)
4. **Narrative timeline** — `dbt compile -s meridian_narrative` / run the compiled SQL  
   (`analyses/meridian_narrative.sql`)
5. **Context engineering** — with AI enabled, `search` retrieves Meridian passages by meaning, optionally filtered to `covenant_or_credit_risk` / `liquidity_or_working_capital`
6. **Governance dashboard** — `make dashboard` for spend, lineage, sensitivity, taxonomy


## Design notes

- **Seeds on BigQuery** — the Cloud demo loads `seeds/*.csv` into BQ (no GCS/BigLake). PDFs in `bronze/documents/` stay in-repo for the story; the warehouse path is catalog + markdown seeds.
- **Physical-copy Bronze** for this demo. Production estates often prefer metadata-only Bronze with selective snapshots — see the article.
- **Silver before vectors** — avoid the Bronze-to-vector shortcut; quality + sensitivity land before embedding.
- **Lineage** — `content_sha256` from Bronze rides through Silver and into chunk metadata so Gold answers can cite a file hash.
- **Classification buys precision** — same lesson as jaffle-logistics: plain cosine recalls boilerplate; a closed taxonomy filters to the passages that matter.

## Requirements

- Python 3.10+
- dbt-core ≥ 1.12 (for `vars.yml`)
- `dbt-duckdb` for local runs; `dbt-bigquery` (or Cloud) for real `embed()` / `classify()`
