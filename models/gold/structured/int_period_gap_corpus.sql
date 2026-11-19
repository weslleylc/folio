-- Hybrid extraction, the GAP: silver_ready docs where the regex found no fiscal period
-- BUT the text mentions a quarter in a shape the regex doesn't understand (period_hint).
-- Docs with no period at all are NOT here — nothing to extract, so no AI call is wasted on them.
{{ config(materialized='view') }}

select
    d.doc_id,
    d.account_id,
    d.doc_type,
    d.title,
    d.content_sha256,
    d.silver_version_id,
    {% if target.type == 'bigquery' -%}
    substr(d.body_sanitized, 1, 2500)
    {%- else -%}
    substring(d.body_sanitized, 1, 2500)
    {%- endif %} as extract_text
from {{ ref('silver_ready_documents') }} d
join {{ ref('gold_document_facts') }} g on g.doc_id = d.doc_id
where g.fiscal_period_regex is null
  and g.period_hint
