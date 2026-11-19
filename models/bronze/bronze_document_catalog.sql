-- 🥉 Bronze: CURRENT catalog — one row per document, always the latest registered version.
-- The immutable history lives in bronze_document_versions (append-only); this view is what
-- Silver reads. A document with n_bronze_versions > 1 was re-sent / revised at the source.
{{ config(materialized='view') }}

with ranked as (
    select
        *,
        max(bronze_version) over (partition by doc_id) as latest_version,
        count(*) over (partition by doc_id) as n_bronze_versions
    from {{ ref('bronze_document_versions') }}
)

select
    doc_id,
    filename,
    relative_path,
    uri,
    doc_type,
    account_id,
    account_name,
    effective_date,
    source_system,
    title,
    mime_type,
    byte_size,
    content_sha256,
    ingested_at,
    bronze_layer,
    ingest_batch,
    bronze_version,
    n_bronze_versions
from ranked
where bronze_version = latest_version
