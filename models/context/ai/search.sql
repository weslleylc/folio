-- Retrieval demos over the financial knowledge base.
-- Raw cosine vs classification-filtered — same before/after pattern as Jaffle.
{% set use_stand_in = ai_stand_in() %}
{% set meridian_query = "cast([0.0, 0.0, 0.0] as double[3])" if use_stand_in else dbt_context_engineering.embed("'" ~ var('search_query_meridian') ~ "'") %}
{{ config(materialized='table') }}

with meridian_raw as (
    select 'meridian_covenant_liquidity_raw' as demo, s.*
    from (
        {{ dbt_context_engineering.vector_search(
            relation=ref('knowledge_base'),
            embedding_column='embedding',
            query_embedding=meridian_query,
            top_k=10,
            id_column='source_id',
            select_columns=['source_type', 'citation_url', 'ts', 'text', 'classification'],
            filter="account_key = '" ~ var('search_account_id') ~ "'"
        ) }}
    ) s
),

meridian_classified as (
    select 'meridian_covenant_liquidity_classified' as demo, s.*
    from (
        {{ dbt_context_engineering.vector_search(
            relation=ref('knowledge_base'),
            embedding_column='embedding',
            query_embedding=meridian_query,
            top_k=10,
            id_column='source_id',
            select_columns=['source_type', 'citation_url', 'ts', 'text', 'classification'],
            filter="account_key = '" ~ var('search_account_id') ~ "' and classification in ('covenant_or_credit_risk', 'liquidity_or_working_capital')"
        ) }}
    ) s
)

select * from meridian_raw
union all
select * from meridian_classified
