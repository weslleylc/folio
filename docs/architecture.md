# Architecture: unstructured medallion → context engineering

Folio applies the [Medallion Architecture to unstructured data](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835) and then uses [`dbt_context_engineering`](https://github.com/dbt-labs/dbt-context-engineering) so an agent (or analyst) can retrieve governed passages with citations.

## Layers (and how they map to the article)

| Layer | Article asks for | Folio |
|---|---|---|
| **Bronze** | Catalog, zero-copy by default, immutable | `bronze_document_versions` — **append-only** log, one row per `(doc_id, content_sha256)`; `bronze_document_catalog` — view of the current version |
| **Silver** | Parse, quality gate, PII redaction, dedup | `silver_document_bodies` — status CASE (parse failed → low quality → PII → **duplicate** → ready), `body_sanitized` (SSN / e-mail spans redacted), `silver_version_id`; `silver_ready_documents` view exposes only sanitized text |
| **Gold · context_store** | Chunks + embeddings, reusable | `documents_hashed`, `documents_embed` (incremental, `access: public`, group `knowledge_platform`) |
| **Gold · structured** | Tables you can join | `gold_document_facts`, `gold_account_risk_rollup`, `gold_document_periods` (hybrid), `documents_extract_flat` |
| **Gold · serving** | Use-case products | `documents_classify`, `knowledge_base`, `search` |
| **Gold · governance** | Lineage, spend, health | `gov_document_lineage`, `gov_ai_spend`, `gov_medallion_health`, `gov_classify_eval` |

## Bronze is append-only

`bronze_document_versions` is incremental and never rewrites a row:

- A row is identified by `(doc_id, content_sha256)`. Registering the same pair twice is a no-op.
- A changed file (same `doc_id`, new hash) becomes `bronze_version + 1`; v1 stays forever.
- `--full-refresh` is disabled unless `allow_bronze_rebuild=true`.
- `tests/assert_bronze_append_only.sql` fails on duplicate or missing versions.
- Batches are simulated with `ingest_batch` in the catalog seed; raise `bronze_max_batch` to "receive" the next one.

Downstream effect (verified): re-issuing invoice INV-4401 adds Bronze v2 → Silver's `silver_version_id` changes → only that document's chunks are re-embedded / re-classified (2 rows billed, not 102). An e-mailed copy of MER-X02 keeps its own Bronze row (provenance) but Silver marks it `quarantine_duplicate`.

## Why not Bronze → vector DB?

Skipping Silver (the article's "Bronze-to-Vector shortcut") would embed past-due notices, boilerplate, SSNs and low-quality parses into the same index. Silver is the governance gate: parse quality, sensitivity, redaction and lineage before any embedding spend.

## Context engineering DAG

```
Bronze versions → current catalog → Silver gate → silver_ready_documents (sanitized)
    → split_sentences → chunk → attach_metadata → content_hash        (free)
    → embed()  → documents_embed  (incremental, reusable by other projects)
    → classify() / vector_search / extract()  → serving + structured   (billed)
```

Two switches keep spend opt-in:

| Var | Builds |
|---|---|
| *(none)* | Everything free: Bronze, Silver, chunks, regex facts, governance views |
| `embeddings_enabled` | + `documents_embed` only (a reusable vector store; decide later how to use it) |
| `ai_functions_enabled` | + classify, search, extract, period fallback, evals (implies embeddings) |

To reuse embeddings from another dbt project, `ref('folio', 'documents_embed')` (public access, group `knowledge_platform`).

## Hybrid extraction: regex first, AI when regex fails

Fiscal period per document (`gold_document_periods`):

1. **regex** (free) reads the canonical wording "… period: Q3 2025" → `fiscal_period_method = 'regex'`.
2. **AI `extract()`** (billed) runs only for documents where the regex found nothing *but* the text mentions "quarter ended …" / "Nth quarter of fiscal …" (`int_period_gap_corpus`) → `'ai'`, with a verbatim quote checked by `grounded`. `documents_period_fallback` is incremental on `(doc_id, silver_version_id, prompt+model version)`.
3. Nothing in the text → `'not_found'`, and no tokens are spent.

## Known gaps vs the article

ACL propagation from the source system · a human steward queue for quarantined files · near-duplicate detection (MinHash; only exact sha256 here) · `documents_extract` (credit signals) is still a plain table that re-bills on each build.

## Demo story

**Meridian Industrial (ACC-8847)** — working-capital stress and covenant headroom erosion, scattered across invoices, a credit-facility amendment, a credit-committee memo, an earnings call, a 10-Q MD&A excerpt, and an analyst note. Noise documents for other accounts keep naive search from being trivial.

1. `analyses/meridian_narrative.sql` — timeline via joins (exact-match ceiling).
2. `models/gold/serving/search.sql` — semantic retrieval with optional classification filter.
