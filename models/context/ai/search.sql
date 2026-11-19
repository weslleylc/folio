-- Retrieval demos over the WHOLE financial knowledge base (all 12 accounts).
-- Same question, same embedding, same top-10 — the only difference is the label filter.
--   raw        = cosine similarity only (recall)
--   classified = cosine similarity + classification filter (precision)
-- Neither filters by account: the analyst asks a plain-words question (no borrower name)
-- and the corpus decides what is relevant. account_key is returned so we can measure pollution.
{% set use_stand_in = ai_stand_in() %}
{% set demo_query = "cast([0.0, 0.0, 0.0] as double[3])" if use_stand_in else dbt_context_engineering.embed("'" ~ var('search_query') ~ "'") %}
{{ config(materialized='table') }}

with raw_search as (
    select 'raw_cosine_only' as demo, s.*
    from (
        {{ dbt_context_engineering.vector_search(
            relation=ref('knowledge_base'),
            embedding_column='embedding',
            query_embedding=demo_query,
            top_k=10,
            id_column='source_id',
            select_columns=['source_type', 'account_key', 'citation_url', 'ts', 'text', 'classification']
        ) }}
    ) s
),

classified_search as (
    select 'cosine_plus_label_filter' as demo, s.*
    from (
        {{ dbt_context_engineering.vector_search(
            relation=ref('knowledge_base'),
            embedding_column='embedding',
            query_embedding=demo_query,
            top_k=10,
            id_column='source_id',
            select_columns=['source_type', 'account_key', 'citation_url', 'ts', 'text', 'classification'],
            filter="classification in ('covenant_or_credit_risk', 'liquidity_or_working_capital')"
        ) }}
    ) s
)

select * from raw_search
union all
select * from classified_search
