-- Small, cost-gated corpus for typed extract(): Meridian silver_ready docs only.
-- Truncate body so guard_batch / Gemini stay cheap for the talk.
{{ config(materialized='view') }}

select
    doc_id,
    account_id,
    doc_type,
    title,
    effective_date,
    citation_url,
    content_sha256,
    sensitivity_label,
    {% if target.type == 'bigquery' -%}
    substr(body_markdown, 1, 3500)
    {%- else -%}
    substring(body_markdown, 1, 3500)
    {%- endif %} as extract_text
from {{ ref('silver_ready_documents') }}
where account_id = 'ACC-8847'
