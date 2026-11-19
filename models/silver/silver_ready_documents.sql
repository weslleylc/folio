-- Silver documents that passed quality / parse / sensitivity gates — the only feed into
-- Gold structured tables and the Gold context store (chunks + embeddings).
-- Exposes the SANITIZED text only: raw body_markdown is deliberately not selected here.
{{ config(materialized='view') }}

select
    doc_id,
    account_id,
    doc_type,
    title,
    effective_date,
    source_system,
    extractor,
    sensitivity_label,
    content_sha256,
    silver_version_id,
    pii_redacted,
    citation_url,
    body_sanitized
from {{ ref('silver_document_bodies') }}
where silver_status = 'silver_ready'
  and body_sanitized is not null
  and length(trim(body_sanitized)) > 0
