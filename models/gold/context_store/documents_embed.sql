-- Governed incremental embedding (REAL AI cost when enabled).
-- DuckDB stand-in keeps parse/build green locally.
{% set use_stand_in = ai_stand_in() %}
{% set fingerprint = dbt_context_engineering.embedding_fn_fingerprint(model=var('embedding_model')) %}
{% set delta = dbt_context_engineering.incremental_delta_predicate(
    'chunk_id', fingerprint, 'embedding_fn_fingerprint', content_hash_column='content_hash') %}

{{ config(
    materialized='incremental',
    unique_key='chunk_id',
    full_refresh=var('allow_full_reembed', false),
    pre_hook=[
        "{{ dbt_context_engineering.guard_batch(ref('documents_hashed'), 'chunk_text', filter=dbt_context_engineering.incremental_delta_predicate('chunk_id', dbt_context_engineering.embedding_fn_fingerprint(model=var('embedding_model')), 'embedding_fn_fingerprint', content_hash_column='content_hash')) }}",
        "{{ dbt_context_engineering.log_ai_run('embed', model_name=var('embedding_model'), relation=ref('documents_hashed'), input_column='chunk_text', filter=dbt_context_engineering.incremental_delta_predicate('chunk_id', dbt_context_engineering.embedding_fn_fingerprint(model=var('embedding_model')), 'embedding_fn_fingerprint', content_hash_column='content_hash')) }}"
    ],
    post_hook="{{ dbt_context_engineering.complete_ai_run('embed', model_name=var('embedding_model')) }}"
) }}

with embedded as (
    select
        chunk_id,
        account_id,
        doc_type,
        title,
        source_type,
        citation_url,
        artifact_ts,
        sensitivity_label,
        bronze_content_sha256,
        silver_version_id,
        chunk_text,
        content_hash,
        {% if use_stand_in -%}
        cast([0.0, 0.0, 0.0] as double[3])
        {%- else -%}
        {{ dbt_context_engineering.embed('chunk_text') }}
        {%- endif %} as embedding
    from {{ ref('documents_hashed') }}
    {% if delta %}where {{ delta }}{% endif %}
)

select
    chunk_id,
    account_id,
    doc_type,
    title,
    source_type,
    citation_url,
    artifact_ts,
    sensitivity_label,
    bronze_content_sha256,
    silver_version_id,
    chunk_text,
    content_hash,
    '{{ var("embedding_model") }}' as model_version,
    embedding,
    {{ dbt_context_engineering.embedding_dimension('embedding') }} as embedding_dimension,
    '{{ fingerprint }}' as embedding_fn_fingerprint,
    '{{ run_started_at }}' as embedded_at,
    '{{ dbt_context_engineering.embedding_logic_hash() }}' as embedding_logic_hash
from embedded
