-- Hybrid extraction, step 2 (billed): AI extract() ONLY for the documents the regex missed.
-- Incremental on (doc_id, silver_version_id, extract_version): a document is sent to the model once;
-- it is re-sent only if its sanitized text, the prompt/schema version, or the model changes.
{% set use_stand_in = ai_stand_in() %}
{% set version = folio_period_version() %}
{% set delta = dbt_context_engineering.incremental_delta_predicate(
    'doc_id', version, 'extract_version', content_hash_column='silver_version_id') %}

{{ config(
    materialized='incremental',
    unique_key='doc_id',
    full_refresh=var('allow_full_reextract', var('allow_full_reembed', false)),
    meta={'ai_prompt': {'name': 'folio_period_extract', 'version': 'v1'}},
    pre_hook=[
        "{{ dbt_context_engineering.guard_batch(ref('int_period_gap_corpus'), 'extract_text', filter=dbt_context_engineering.incremental_delta_predicate('doc_id', folio_period_version(), 'extract_version', content_hash_column='silver_version_id')) }}",
        "{{ dbt_context_engineering.log_ai_run('extract', model_name=var('model_extract', var('model_generate')), relation=ref('int_period_gap_corpus'), input_column='extract_text', filter=dbt_context_engineering.incremental_delta_predicate('doc_id', folio_period_version(), 'extract_version', content_hash_column='silver_version_id'), prompt=dbt_context_engineering.prompt('folio_period_extract', 'v1')) }}"
    ],
    post_hook="{{ dbt_context_engineering.complete_ai_run('extract', model_name=var('model_extract', var('model_generate'))) }}"
) }}

with extracted as (
    select
        doc_id,
        account_id,
        doc_type,
        title,
        content_sha256,
        silver_version_id,
        extract_text,
        {% if use_stand_in -%}
        '{"fiscal_year":"","fiscal_quarter":"","evidence":""}'
        {%- else -%}
        {{ dbt_context_engineering.extract(
            'extract_text',
            prompt=dbt_context_engineering.prompt('folio_period_extract', 'v1'),
            output_schema=dbt_context_engineering.schema_def('folio_period_extract', 'v1'),
            model=var('model_extract', var('model_generate'))
        ) }}
        {%- endif %} as extracted
    from {{ ref('int_period_gap_corpus') }}
    {% if delta %}where {{ delta }}{% endif %}
)

select
    x.doc_id,
    x.account_id,
    x.doc_type,
    x.title,
    x.content_sha256,
    x.silver_version_id,
    '{{ version }}' as extract_version,
    x.extract_text,
    {{ dbt_context_engineering.field('x.extracted', 'fiscal_year') }} as fiscal_year,
    {{ dbt_context_engineering.field('x.extracted', 'fiscal_quarter') }} as fiscal_quarter,
    {{ dbt_context_engineering.field('x.extracted', 'evidence') }} as evidence,
    '{{ run_started_at }}' as extracted_at
from extracted x
