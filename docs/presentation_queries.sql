-- Folio presentation queries — BigQuery Studio
-- Dataset from your dbt Cloud run. Change if needed:
--   project:  roundtable-513102
--   dataset:  dbt_wcaldas
--
-- Tip: save each block as a starred query named 01_bronze … 07_spend
--      so you can click through live without retyping.

-- =============================================================================
-- 01  BRONZE — provenance only (zero-copy talking point: uri + sha256)
-- Chart: none (table). Point at uri / content_sha256 / bronze_layer.
-- =============================================================================
select
  doc_id,
  doc_type,
  account_id,
  account_name,
  effective_date,
  source_system,
  uri,
  content_sha256,
  bronze_layer
from `roundtable-513102.dbt_wcaldas.bronze_document_catalog`
order by effective_date, doc_id;


-- =============================================================================
-- 02  SILVER — quality + sensitivity gate (quarantine before vectors)
-- Chart: Bar — X=doc_id, Y=quality_score (or stacked by silver_status)
-- =============================================================================
select
  doc_id,
  account_id,
  doc_type,
  quality_score,
  sensitivity_label,
  silver_status,
  page_count
from `roundtable-513102.dbt_wcaldas.silver_document_bodies`
order by quality_score, doc_id;


-- =============================================================================
-- 03  GOLD ROLLUP — Meridian stands out vs noise accounts
-- Chart: Bar — X=account_name, Y=covenant_docs (or grouped bars)
-- =============================================================================
select
  account_id,
  account_name,
  sector,
  document_count,
  past_due_docs,
  covenant_docs,
  liquidity_docs,
  max_leverage_mentioned,
  max_risk_tier,
  latest_doc_date
from `roundtable-513102.dbt_wcaldas.gold_account_risk_rollup`
order by
  case max_risk_tier when 'high' then 3 when 'medium' then 2 when 'low' then 1 else 0 end desc,
  covenant_docs desc,
  past_due_docs desc;


-- =============================================================================
-- 04  GOLD FACTS — per-doc flags (regex ceiling)
-- Chart: Table, or stacked bar by risk_signal_tier
-- =============================================================================
select
  doc_id,
  account_id,
  doc_type,
  effective_date,
  flag_past_due,
  flag_covenant_language,
  flag_liquidity_language,
  leverage_ratio_mention,
  first_usd_amount,
  risk_signal_tier
from `roundtable-513102.dbt_wcaldas.gold_document_facts`
where account_id = 'ACC-8847'
order by effective_date;


-- =============================================================================
-- 05  NARRATIVE TIMELINE — join/regex ceiling (not semantic search)
-- Chart: none (table). Say: "timeline yes; meaning across PDFs no."
-- =============================================================================
with catalog as (
  select
    cast(effective_date as timestamp) as occurred_at,
    'bronze_catalog' as source,
    doc_id as artifact_id,
    title as snippet
  from `roundtable-513102.dbt_wcaldas.bronze_document_catalog`
  where account_id = 'ACC-8847'
),
silver as (
  select
    cast(effective_date as timestamp) as occurred_at,
    'silver_body' as source,
    doc_id as artifact_id,
    substr(body_markdown, 1, 160) as snippet
  from `roundtable-513102.dbt_wcaldas.silver_ready_documents`
  where account_id = 'ACC-8847'
),
gold_facts as (
  select
    cast(effective_date as timestamp) as occurred_at,
    'gold_fact' as source,
    doc_id as artifact_id,
    concat(
      'tier=', risk_signal_tier,
      ' past_due=', cast(flag_past_due as string),
      ' covenant=', cast(flag_covenant_language as string),
      ' liquidity=', cast(flag_liquidity_language as string),
      if(leverage_ratio_mention is null, '', concat(' leverage=', cast(leverage_ratio_mention as string)))
    ) as snippet
  from `roundtable-513102.dbt_wcaldas.gold_document_facts`
  where account_id = 'ACC-8847'
)
select * from catalog
union all
select * from silver
union all
select * from gold_facts
order by occurred_at, source;


-- =============================================================================
-- 06a  SEARCH RAW — cosine only (often boilerplate)
-- Chart: Bar — X=source_id (or classification), Y=score
-- =============================================================================
select
  demo,
  source_id,
  classification,
  round(score, 4) as score,
  citation_url,
  substr(text, 1, 160) as snippet
from `roundtable-513102.dbt_wcaldas.search`
where demo = 'meridian_covenant_liquidity_raw'
order by score desc;


-- =============================================================================
-- 06b  SEARCH CLASSIFIED — precision filter (the "aha")
-- Same query shape; compare classifications + top snippets side by side.
-- Chart: Bar — score by classification (side-by-side with 06a in Looker)
-- =============================================================================
select
  demo,
  source_id,
  classification,
  round(score, 4) as score,
  citation_url,
  substr(text, 1, 160) as snippet
from `roundtable-513102.dbt_wcaldas.search`
where demo = 'meridian_covenant_liquidity_classified'
order by score desc;


-- =============================================================================
-- 06c  BEFORE / AFTER in one glance
-- Chart: Stacked bar — demo × classification counts
-- =============================================================================
select
  demo,
  classification,
  count(*) as hits,
  round(avg(score), 4) as avg_score,
  round(max(score), 4) as max_score
from `roundtable-513102.dbt_wcaldas.search`
group by 1, 2
order by demo, hits desc;


-- =============================================================================
-- 07  TAXONOMY MIX — closed labels as a product decision
-- Chart: Pie or donut — classification × chunk_count
-- =============================================================================
select
  classification,
  chunk_count,
  accounts,
  documents,
  round(avg_chunk_chars, 0) as avg_chunk_chars
from `roundtable-513102.dbt_wcaldas.gov_classification_breakdown`
order by chunk_count desc;


-- =============================================================================
-- 08  AI SPEND — cost gates made visible
-- Chart: Bar — function_name × est_cost_usd (or est_tokens)
-- =============================================================================
select
  function_name,
  model_name,
  row_count,
  round(est_tokens, 0) as est_tokens,
  round(est_cost_usd, 6) as est_cost_usd,
  cost_source,
  completed,
  started_at
from `roundtable-513102.dbt_wcaldas.gov_ai_spend`
order by started_at;


-- =============================================================================
-- 09  LINEAGE / RTBF drill — Meridian docs → chunks → hash
-- Chart: none (table). Point at content_sha256 for citation / purge story.
-- =============================================================================
select
  doc_id,
  account_id,
  content_sha256,
  chunk_count,
  lineage_status
from `roundtable-513102.dbt_wcaldas.gov_document_lineage`
where account_id = 'ACC-8847'
order by doc_id;


-- =============================================================================
-- 10  MEDALLION HEALTH — one-row executive snapshot
-- Chart: Scorecard metrics in Looker Studio (bronze_docs, pct_silver_ready, …)
-- =============================================================================
select *
from `roundtable-513102.dbt_wcaldas.gov_medallion_health`;
