-- Typed extraction via dbt_context_engineering.extract() (package: Beta, ADR-0010).
-- Real AI cost when ai_functions_enabled; DuckDB uses a deterministic stand-in.
{% set use_stand_in = ai_stand_in() %}

{{ config(
    materialized='table',
    meta={'ai_prompt': {'name': 'folio_credit_extract', 'version': 'v1'}},
    pre_hook=[
        "{{ dbt_context_engineering.guard_batch(ref('int_extract_corpus'), 'extract_text') }}",
        "{{ dbt_context_engineering.log_ai_run('extract', model_name=var('model_generate'), relation=ref('int_extract_corpus'), input_column='extract_text', prompt=dbt_context_engineering.prompt('folio_credit_extract', 'v1')) }}"
    ],
    post_hook="{{ dbt_context_engineering.complete_ai_run('extract', model_name=var('model_generate')) }}"
) }}

select
    doc_id,
    account_id,
    doc_type,
    title,
    effective_date,
    citation_url,
    content_sha256,
    silver_version_id,
    sensitivity_label,
    extract_text,
    {% if use_stand_in -%}
    case
        when lower(extract_text) like '%past due%'
          or lower(extract_text) like '%overdue%'
          or lower(extract_text) like '%credit hold%'
            then '{"primary_signal":"collections_past_due","leverage_mention":"","usd_amount_mention":"","evidence":"past due"}'
        when lower(extract_text) like '%covenant%'
          or lower(extract_text) like '%leverage%'
            then '{"primary_signal":"covenant_pressure","leverage_mention":"","usd_amount_mention":"","evidence":"covenant"}'
        when lower(extract_text) like '%liquidity%'
          or lower(extract_text) like '%working capital%'
          or lower(extract_text) like '%dso%'
            then '{"primary_signal":"liquidity_stress","leverage_mention":"","usd_amount_mention":"","evidence":"liquidity"}'
        when lower(extract_text) like '%10-q%'
          or lower(extract_text) like '%earnings call%'
            then '{"primary_signal":"disclosure_only","leverage_mention":"","usd_amount_mention":"","evidence":"disclosure"}'
        else '{"primary_signal":"none","leverage_mention":"","usd_amount_mention":"","evidence":"n/a"}'
    end
    {%- else -%}
    {{ dbt_context_engineering.extract(
        'extract_text',
        prompt=dbt_context_engineering.prompt('folio_credit_extract', 'v1'),
        output_schema=dbt_context_engineering.schema_def('folio_credit_extract', 'v1'),
        model=var('model_extract', var('model_generate'))
    ) }}
    {%- endif %} as extracted
from {{ ref('int_extract_corpus') }}
