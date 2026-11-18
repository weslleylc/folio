-- Attach account / citation / sensitivity metadata onto every chunk.
{{ config(materialized='table') }}

{{ dbt_context_engineering.attach_metadata(
    chunks_relation=ref('chunk_documents'),
    metadata_relation=ref('int_documents'),
    metadata_key_column='doc_id',
    metadata_columns=['account_id', 'doc_type', 'title', 'citation_url', 'artifact_ts', 'sensitivity_label', 'content_sha256']
) }}
