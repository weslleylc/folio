# Architecture: unstructured medallion → context engineering

Folio applies the [Medallion Architecture to unstructured data](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835) and then uses [`dbt_context_engineering`](https://github.com/dbt-labs/dbt-context-engineering) so an agent (or analyst) can retrieve governed passages with citations.

## Layers

| Layer | What lives here | Folio path |
|---|---|---|
| **Bronze** | Raw PDFs + catalog (URI, SHA-256, mime, provenance). No interpretation. | `bronze/documents/`, `bronze_document_catalog` |
| **Silver** | Docling markdown, quality score, sensitivity label, quarantine status | `silver/extracted/`, `silver_document_bodies`, `silver_ready_documents` |
| **Gold** | Structured facts + risk rollups **and** chunk → embed → classify → knowledge_base → search | `gold_*`, `models/context/` |

## Why not Bronze → vector DB?

Skipping Silver (the article's "Bronze-to-Vector shortcut") would embed past-due notices, boilerplate, and low-quality parses into the same index. Silver is the governance gate: parse quality, sensitivity tags, and lineage (`content_sha256`) before any embedding spend.

## Context engineering DAG

```
Silver-ready docs
    → split_sentences → chunk → attach_metadata → content_hash
    → embed() + classify()          # gated: ai_functions_enabled
    → knowledge_base → vector_search
```

Deterministic path (no AI bill): everything through `documents_hashed` plus Gold SQL facts.  
Billed path: `models/context/ai/*` when `ai_functions_enabled: true` on Snowflake / BigQuery / Databricks.

## Demo story

**Meridian Industrial (ACC-8847)** — working-capital stress and covenant headroom erosion, scattered across invoices, a credit-facility amendment, a credit-committee memo, an earnings call, a 10-Q MD&A excerpt, and an analyst note. Noise documents for other accounts keep naive search from being trivial.

1. `analyses/meridian_narrative.sql` — timeline via joins (exact-match ceiling).
2. `models/context/ai/search.sql` — semantic retrieval with optional classification filter.
