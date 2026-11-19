-- Layer-1 splitter (deterministic, zero AI cost): one row per sentence.
{{ config(materialized='table') }}

{{ dbt_context_engineering.split_sentences(
    relation=ref('int_documents'),
    id_column='doc_id',
    text_column='body'
) }}
