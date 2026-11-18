-- Governance KPIs across Bronze / Silver / Gold (article pillars:
-- discovery, quality, privacy labels, lineage, SLA-ish freshness).
{{ config(materialized='table') }}

with bronze as (
    select
        count(*) as bronze_docs,
        count(distinct account_id) as bronze_accounts,
        count(distinct source_system) as bronze_source_systems,
        count(distinct doc_type) as bronze_doc_types,
        sum(byte_size) as bronze_bytes,
        max(ingested_at) as bronze_last_ingest
    from {{ ref('bronze_document_catalog') }}
),

silver as (
    select
        count(*) as silver_docs,
        sum(case when silver_status = 'silver_ready' then 1 else 0 end) as silver_ready,
        sum(case when silver_status != 'silver_ready' then 1 else 0 end) as silver_quarantined,
        avg(quality_score) as avg_quality_score,
        min(quality_score) as min_quality_score,
        max(extracted_at) as silver_last_extract,
        sum(case when sensitivity_label = 'restricted_pii' then 1 else 0 end) as sens_restricted_pii,
        sum(case when sensitivity_label = 'confidential' then 1 else 0 end) as sens_confidential,
        sum(case when sensitivity_label = 'public_market' then 1 else 0 end) as sens_public_market,
        sum(case when sensitivity_label = 'internal' then 1 else 0 end) as sens_internal,
        sum(case when extractor = 'docling' then 1 else 0 end) as extracted_via_docling,
        sum(case when extractor != 'docling' then 1 else 0 end) as extracted_via_fallback
    from {{ ref('silver_document_bodies') }}
),

gold as (
    select
        count(*) as gold_fact_docs,
        sum(case when risk_signal_tier = 'high' then 1 else 0 end) as gold_high_risk,
        sum(case when risk_signal_tier = 'medium' then 1 else 0 end) as gold_medium_risk,
        sum(case when risk_signal_tier = 'low' then 1 else 0 end) as gold_low_risk,
        sum(case when flag_covenant_language then 1 else 0 end) as gold_covenant_flags,
        sum(case when flag_liquidity_language then 1 else 0 end) as gold_liquidity_flags,
        sum(case when flag_past_due then 1 else 0 end) as gold_past_due_flags
    from {{ ref('gold_document_facts') }}
),

context_layer as (
    select
        (select count(*) from {{ ref('documents_hashed') }}) as hashed_chunks,
        (select count(distinct partition_key) from {{ ref('documents_hashed') }}) as hashed_docs
),

ai_layer as (
    select
        (select count(*) from {{ ref('gov_ai_spend') }}) as ai_started_runs,
        (select coalesce(sum(est_tokens), 0) from {{ ref('gov_ai_spend') }}) as ai_total_est_tokens,
        (select coalesce(sum(est_cost_usd), 0) from {{ ref('gov_ai_spend') }}) as ai_total_est_cost_usd,
        (select sum(case when not completed then 1 else 0 end) from {{ ref('gov_ai_spend') }}) as ai_orphaned_starts
)

select
    current_timestamp as snapshot_at,
    b.*,
    s.*,
    g.*,
    c.*,
    a.*,
    case when b.bronze_docs = 0 then null
         else cast(s.silver_docs as double) / b.bronze_docs
    end as pct_bronze_in_silver,
    case when s.silver_docs = 0 then null
         else cast(s.silver_ready as double) / s.silver_docs
    end as pct_silver_ready,
    case when s.silver_docs = 0 then null
         else cast(s.silver_quarantined as double) / s.silver_docs
    end as pct_quarantined,
    case when b.bronze_docs = 0 then null
         else cast(g.gold_fact_docs as double) / b.bronze_docs
    end as pct_bronze_in_gold
from bronze b
cross join silver s
cross join gold g
cross join context_layer c
cross join ai_layer a
