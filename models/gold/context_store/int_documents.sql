-- Reshape Silver-ready docs for the chunk pipeline. One independent corpus
-- path (all Docling-extracted financial docs) ending in knowledge_base.
{{ config(materialized='view') }}

select
    doc_id,
    account_id,
    doc_type,
    title,
    body_sanitized as body,
    cast(effective_date as {{ dbt.type_timestamp() }}) as artifact_ts,
    citation_url,
    content_sha256,
    silver_version_id,
    sensitivity_label
from {{ ref('silver_ready_documents') }}
