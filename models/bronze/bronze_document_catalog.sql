-- 🥉 Bronze: immutable catalog of unstructured financial assets.
-- Metadata-first registry (URI, hash, mime, provenance). Binaries stay in
-- bronze/documents/; this table never stores file bytes.
{{ config(materialized='table') }}

select
    doc_id,
    filename,
    relative_path,
    uri,
    doc_type,
    account_id,
    account_name,
    cast(effective_date as date) as effective_date,
    source_system,
    title,
    mime_type,
    cast(byte_size as bigint) as byte_size,
    content_sha256,
    cast(ingested_at as timestamp) as ingested_at,
    bronze_layer
from {{ ref('raw_document_catalog') }}
