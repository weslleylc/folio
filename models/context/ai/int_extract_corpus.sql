-- Small, cost-gated corpus for typed extract() — silver_ready docs only:
--   * every Meridian doc (the story), plus
--   * every NON-Meridian doc that the Gold regex flagged (the false-positive test:
--     does extract() agree with the regex, or does it see the doc is actually healthy?)
-- Body truncated so guard_batch / Gemini stay cheap for the talk.
{{ config(materialized='view') }}

select
    d.doc_id,
    d.account_id,
    d.doc_type,
    d.title,
    d.effective_date,
    d.citation_url,
    d.content_sha256,
    d.sensitivity_label,
    {% if target.type == 'bigquery' -%}
    substr(d.body_markdown, 1, 3500)
    {%- else -%}
    substring(d.body_markdown, 1, 3500)
    {%- endif %} as extract_text
from {{ ref('silver_ready_documents') }} d
join {{ ref('gold_document_facts') }} g on g.doc_id = d.doc_id
where d.account_id = 'ACC-8847'
   or g.risk_signal_tier != 'low'
