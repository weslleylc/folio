-- Flatten extract() STRUCT/JSON → scalars via field(); keeps source text for grounded().
{{ config(materialized='table') }}

select
    e.doc_id,
    e.account_id,
    e.doc_type,
    e.title,
    e.effective_date,
    e.citation_url,
    e.content_sha256,
    e.silver_version_id,
    e.sensitivity_label,
    e.extract_text,
    {{ dbt_context_engineering.field('e.extracted', 'primary_signal') }} as primary_signal,
    {{ dbt_context_engineering.field('e.extracted', 'leverage_mention') }} as leverage_mention,
    {{ dbt_context_engineering.field('e.extracted', 'usd_amount_mention') }} as usd_amount_mention,
    {{ dbt_context_engineering.field('e.extracted', 'evidence') }} as evidence
from {{ ref('documents_extract') }} e
