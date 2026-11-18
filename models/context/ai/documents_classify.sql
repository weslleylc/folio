-- Classify each chunk into the Folio financial taxonomy (REAL AI cost when enabled).
{% set use_stand_in = ai_stand_in() %}

{{ config(
    materialized='table',
    meta={'ai_prompt': {'name': 'folio_content_type', 'version': 'v1'}},
    pre_hook=[
        "{{ dbt_context_engineering.guard_batch(ref('documents_hashed'), 'chunk_text') }}",
        "{{ dbt_context_engineering.log_ai_run('classify', model_name='ai_classify (built-in)', relation=ref('documents_hashed'), input_column='chunk_text', prompt=dbt_context_engineering.prompt('folio_content_type', 'v1')) }}"
    ],
    post_hook="{{ dbt_context_engineering.complete_ai_run('classify', model_name='ai_classify (built-in)') }}"
) }}

select
    chunk_id,
    {% if use_stand_in -%}
    case
        when lower(chunk_text) like '%covenant%'
          or lower(chunk_text) like '%leverage%'
          or lower(chunk_text) like '%credit committee%'
            then 'covenant_or_credit_risk'
        when lower(chunk_text) like '%working capital%'
          or lower(chunk_text) like '%liquidity%'
          or lower(chunk_text) like '%dso%'
          or lower(chunk_text) like '%receivable%'
            then 'liquidity_or_working_capital'
        when lower(chunk_text) like '%past due%'
          or lower(chunk_text) like '%overdue%'
          or lower(chunk_text) like '%credit hold%'
          or lower(chunk_text) like '%invoice%'
            then 'supplier_collections'
        when lower(chunk_text) like '%10-q%'
          or lower(chunk_text) like '%earnings call%'
          or lower(chunk_text) like '%form 10%'
            then 'public_disclosure'
        else 'routine_transaction'
    end
    {%- else -%}
    {{ dbt_context_engineering.classify(
        'chunk_text',
        prompt=dbt_context_engineering.prompt('folio_content_type', 'v1'),
        output_schema=dbt_context_engineering.schema_def('folio_content_type', 'v1')
    ) }}
    {%- endif %} as content_type
from {{ ref('documents_hashed') }}
