-- content_hash upstream of embed() so incremental re-embeds detect text drift.
{{ config(materialized='view', docs={'node_color': '#7FAFAF'}) }}

select
    chunk_id,
    partition_key,
    account_id,
    doc_type,
    title,
    chunk_text,
    'financial_document' as source_type,
    citation_url,
    artifact_ts,
    sensitivity_label,
    content_sha256 as bronze_content_sha256,
    {{ dbt_context_engineering.content_hash('chunk_text') }} as content_hash
from {{ ref('documents_chunks_meta') }}
where chunk_text is not null
  and length(trim(chunk_text)) > 0
