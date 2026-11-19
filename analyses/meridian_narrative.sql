-- NARRATIVE query (the "signal"): every Silver/Gold artifact touching
-- Meridian Industrial (ACC-8847), in date order — reconstructed from the
-- unstructured medallion, not from a single system of record.
--
-- This is the join/regex ceiling: you can stitch a timeline from catalog
-- metadata + risk flags. What you still cannot do well is "find passages
-- about covenant headroom across mixed PDFs by meaning" — that payoff is
-- models/gold/serving/search.sql via dbt_context_engineering.

{% set meridian = "'ACC-8847'" %}

with catalog as (
    select
        cast(effective_date as timestamp) as occurred_at,
        'bronze_catalog' as source,
        doc_id as artifact_id,
        account_id as ref_id,
        title as snippet
    from {{ ref('bronze_document_catalog') }}
    where account_id = {{ meridian }}
),

silver as (
    select
        cast(effective_date as timestamp) as occurred_at,
        'silver_body' as source,
        doc_id as artifact_id,
        account_id as ref_id,
        left(body_sanitized, 160) as snippet
    from {{ ref('silver_ready_documents') }}
    where account_id = {{ meridian }}
),

gold_facts as (
    select
        cast(effective_date as timestamp) as occurred_at,
        'gold_fact' as source,
        doc_id as artifact_id,
        account_id as ref_id,
        'tier=' || risk_signal_tier
            || ' past_due=' || cast(flag_past_due as {{ dbt.type_string() }})
            || ' covenant=' || cast(flag_covenant_language as {{ dbt.type_string() }})
            || ' liquidity=' || cast(flag_liquidity_language as {{ dbt.type_string() }})
            || coalesce(' leverage=' || cast(leverage_ratio_mention as {{ dbt.type_string() }}), '')
            as snippet
    from {{ ref('gold_document_facts') }}
    where account_id = {{ meridian }}
)

select * from catalog
union all
select * from silver
union all
select * from gold_facts
order by occurred_at, source
