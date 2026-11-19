-- Folio presentation queries — BigQuery Studio
-- Project: roundtable-513102   Dataset: dbt_wcaldas  (change both if needed)
--
-- Order = Streamlit page order (see docs/presentation.md).
-- Save each block as a starred query: 02_case, 05_bronze, 06_silver ... so you can click through live.
--
-- Page ↔ query map
--   2  The case ............ 02a, 02b
--   4  Bronze .............. 04, 04b, 04c  (page 5 = discovery, no SQL)
--   6  Silver gate ......... 06a, 06b
--   7  Gold flags .......... 07a, 07b, 07c
--   8  Embeddings .......... 08a, 08b
--   9  Taxonomy ............ 09
--   10 Search .............. 10a, 10b
--   11 Extraction .......... 11, 11b
--   12 Evals ............... 12a, 12b
--   13 Cost & lineage ...... 13a, 13b
--   14 Wrap-up ............. 14


-- =============================================================================
-- 02a  THE CASE — how many files per borrower? (needle in a haystack)
-- Chart: horizontal bar. Y = account_name, X = docs. Highlight ACC-8847.
-- =============================================================================
select account_id, account_name, count(*) as docs
from `roundtable-513102.dbt_wcaldas.bronze_document_catalog`
group by 1, 2
order by docs desc;


-- =============================================================================
-- 02b  THE CASE — Meridian's case file (what an analyst must read)
-- Chart: none (table). Point at the 6 formats + the one quarantined memo.
-- =============================================================================
select b.doc_id, b.doc_type, b.title, b.effective_date, s.silver_status
from `roundtable-513102.dbt_wcaldas.bronze_document_catalog` b
join `roundtable-513102.dbt_wcaldas.silver_document_bodies` s using (doc_id)
where b.account_id = 'ACC-8847'
order by b.effective_date;


-- =============================================================================
-- 04  BRONZE — provenance only: uri + sha256, no interpretation
-- Chart: none (table). Point at uri / content_sha256 / bronze_layer.
-- =============================================================================
select doc_id, doc_type, account_id, account_name, effective_date,
       source_system, uri, content_sha256, bronze_layer
from `roundtable-513102.dbt_wcaldas.bronze_document_catalog`
order by effective_date, doc_id;


-- =============================================================================
-- 04b  BRONZE — append-only history: a revised file is a NEW version, v1 is kept
-- Chart: none (table). INV-4401 has v1 + v2 with different hashes.
-- =============================================================================
select doc_id, bronze_version, ingest_batch, source_system,
       substr(content_sha256, 1, 12) as sha256_prefix, bronze_registered_at
from `roundtable-513102.dbt_wcaldas.bronze_document_versions`
where doc_id in (
  select doc_id from `roundtable-513102.dbt_wcaldas.bronze_document_versions` group by 1 having count(*) > 1
)
order by doc_id, bronze_version;


-- =============================================================================
-- 04c  BRONZE — identical bytes arriving twice (kept in Bronze, quarantined in Silver)
-- =============================================================================
select v.doc_id, v.source_system, substr(v.content_sha256, 1, 12) as sha256_prefix, s.silver_status
from `roundtable-513102.dbt_wcaldas.bronze_document_versions` v
join `roundtable-513102.dbt_wcaldas.silver_document_bodies` s using (doc_id)
where v.content_sha256 in (
  select content_sha256 from `roundtable-513102.dbt_wcaldas.bronze_document_versions`
  group by 1 having count(distinct doc_id) > 1
)
order by sha256_prefix, v.ingest_batch;


-- =============================================================================
-- 06a  SILVER GATE — what did the gate decide?
-- Chart: waffle (one square per file) or a simple bar of counts. Green = silver_ready.
-- The gate is the CASE expression in models/silver/silver_document_bodies.sql
-- (first match wins: parse failed → low quality (<0.4) → restricted_pii → duplicate sha256 → ready).
-- =============================================================================
select silver_status, count(*) as docs
from `roundtable-513102.dbt_wcaldas.silver_document_bodies`
group by 1
order by docs desc;


-- =============================================================================
-- 06b  SILVER GATE — the quarantined files and why
-- Chart: none (table).
-- =============================================================================
select doc_id, account_id, parse_status, quality_score, sensitivity_label, silver_status, title
from `roundtable-513102.dbt_wcaldas.silver_document_bodies`
where silver_status != 'silver_ready'
order by silver_status;


-- =============================================================================
-- 07a  GOLD — documents per borrower, split by tier (each document counted once)
-- Chart: stacked bar. Y = account_name, X = docs, colour = risk_signal_tier.
-- =============================================================================
select r.account_name, g.risk_signal_tier, count(*) as docs
from `roundtable-513102.dbt_wcaldas.gold_document_facts` g
join `roundtable-513102.dbt_wcaldas.gold_account_risk_rollup` r using (account_id)
group by 1, 2
order by r.account_name,
         case g.risk_signal_tier when 'high' then 1 when 'medium' then 2 else 3 end;


-- =============================================================================
-- 07b  GOLD — documents per regex tier
-- Chart: bar. Y = tier (high/medium/low), X = docs.
-- high = covenant AND liquidity words · medium = any one flag · low = none.
-- =============================================================================
select risk_signal_tier, count(*) as docs
from `roundtable-513102.dbt_wcaldas.gold_document_facts`
group by 1
order by case risk_signal_tier when 'high' then 1 when 'medium' then 2 else 3 end;


-- =============================================================================
-- 07c  GOLD — Meridian documents and their flags
-- Chart: heatmap. Y = doc_id, X = the three flags, cell red when true.
-- =============================================================================
select doc_id, doc_type, flag_past_due, flag_covenant_language, flag_liquidity_language,
       leverage_ratio_mention, risk_signal_tier, effective_date
from `roundtable-513102.dbt_wcaldas.gold_document_facts`
where account_id = 'ACC-8847'
order by case risk_signal_tier when 'high' then 3 when 'medium' then 2 else 1 end desc,
         effective_date desc;


-- =============================================================================
-- 08a  EMBEDDINGS — what a vector row looks like
-- Chart: none (table). Point at embedding_dimension (768), model_version, content_hash.
-- =============================================================================
select chunk_id, account_id, embedding_dimension, model_version,
       substr(chunk_text, 1, 100) as preview, content_hash
from `roundtable-513102.dbt_wcaldas.documents_embed`
where account_id = 'ACC-8847'
order by chunk_id
limit 10;


-- =============================================================================
-- 08b  EMBEDDINGS — nearest neighbours of one chunk (proof of "meaning")
-- Chart: bar. Y = chunk_id, X = similarity, colour = doc_type.
-- Anchor = MER-X01::1, a past-due invoice. Neighbours should be other invoices.
-- =============================================================================
with anchor as (
  select embedding as e
  from `roundtable-513102.dbt_wcaldas.documents_embed`
  where chunk_id = 'MER-X01::1'
)
select d.chunk_id, d.account_id, d.doc_type,
       round(1 - ML.DISTANCE(d.embedding, a.e, 'COSINE'), 3) as similarity,
       substr(replace(d.chunk_text, '\n', ' '), 1, 110) as preview
from `roundtable-513102.dbt_wcaldas.documents_embed` d, anchor a
order by similarity desc
limit 10;


-- =============================================================================
-- 09  TAXONOMY — closed labels (a product decision)
-- Chart: bar. Y = classification, X = chunk_count.
-- =============================================================================
select classification, chunk_count, accounts, documents, avg_chunk_chars
from `roundtable-513102.dbt_wcaldas.gov_classification_breakdown`
order by chunk_count desc;


-- =============================================================================
-- 10a  SEARCH — who shows up in the top 10? (raw vs filtered)
-- Question: "Which borrower is at risk of default?"
-- Chart: stacked bar. X = demo, Y = results, colour = Meridian vs other borrowers.
-- =============================================================================
select demo,
       count(*) as hits,
       countif(account_key = 'ACC-8847')  as meridian_hits,
       countif(account_key != 'ACC-8847') as other_borrower_hits
from `roundtable-513102.dbt_wcaldas.search`
group by 1
order by demo;


-- =============================================================================
-- 10b  SEARCH — the actual rows, side by side
-- Look at account_key: anything other than ACC-8847 is noise for this question.
-- =============================================================================
select demo, source_id, account_key, classification, round(score, 3) as score,
       substr(replace(text, '\n', ' '), 1, 140) as snippet
from `roundtable-513102.dbt_wcaldas.search`
order by demo, score desc;


-- =============================================================================
-- 11  EXTRACTION — regex tier vs extract() signal, with evidence quote
-- Chart: bar. Y = verdict (agree / regex false alarm / regex missed it), X = docs.
-- =============================================================================
select g.doc_id, g.account_id, g.title,
       g.risk_signal_tier as regex_tier,
       e.primary_signal   as extract_signal,
       e.leverage_mention, e.usd_amount_mention,
       substr(e.evidence, 1, 160) as evidence,
       case
         when g.risk_signal_tier != 'low' and e.primary_signal in ('none', 'disclosure_only') then 'regex false alarm'
         when g.risk_signal_tier  = 'low' and e.primary_signal not in ('none', 'disclosure_only') then 'regex missed it'
         else 'agree'
       end as verdict
from `roundtable-513102.dbt_wcaldas.gold_document_facts` g
join `roundtable-513102.dbt_wcaldas.documents_extract_flat` e using (doc_id)
order by verdict, g.doc_id;


-- =============================================================================
-- 12a  EVALS — precision / recall / accuracy against the golden set
-- Chart: grouped bar. Y = label, X = score, colour = precision / recall.
-- NULL precision = the model never predicted that label for the golden docs.
-- =============================================================================
select metric, label, value
from `roundtable-513102.dbt_wcaldas.gov_classify_eval`
order by metric, label;


-- =============================================================================
-- 12b  EVALS — where did it miss?
-- Chart: none (table). Expect 10Q-Q3-MDA and EARN-Q3-2025.
-- =============================================================================
select doc_id, expected_label, predicted_label, is_correct, chunk_votes
from `roundtable-513102.dbt_wcaldas.gov_classify_eval_pairs`
order by is_correct, doc_id;


-- =============================================================================
-- 13a  COST — AI ledger (started / completed per function)
-- Chart: bar. Y = function_name, X = est_tokens.
-- =============================================================================
select function_name, model_name, row_count, est_tokens, est_cost_usd, cost_source, completed
from `roundtable-513102.dbt_wcaldas.gov_ai_spend`
order by started_at;


-- =============================================================================
-- 13b  LINEAGE — Meridian docs → chunks → sha256 (citation / RTBF drill)
-- Chart: none (table).
-- =============================================================================
select doc_id, content_sha256, chunk_count, lineage_status, risk_signal_tier
from `roundtable-513102.dbt_wcaldas.gov_document_lineage`
where account_id = 'ACC-8847'
order by doc_id;


-- =============================================================================
-- 14  WRAP-UP — one-row executive snapshot (document funnel + AI cost)
-- Chart: funnel bar from bronze_docs → silver_ready → gold_fact_docs → flagged.
-- =============================================================================
select bronze_docs, silver_ready, silver_quarantined, gold_fact_docs,
       gold_high_risk + gold_medium_risk as gold_flagged,
       ai_total_est_tokens, ai_total_est_cost_usd, ai_orphaned_starts
from `roundtable-513102.dbt_wcaldas.gov_medallion_health`;


-- =============================================================================
-- 11b  EXTRACTION (hybrid) — fiscal period: regex first, AI only for the gap
-- Chart: bar. Y = fiscal_period_method, X = docs. Green regex · blue ai · grey not_found.
-- =============================================================================
select fiscal_period_method, count(*) as docs
from `roundtable-513102.dbt_wcaldas.gold_document_periods`
group by 1
order by docs desc;

-- The AI rescues, with the verbatim quote that backs each period:
select doc_id, fiscal_period_ai, ai_evidence
from `roundtable-513102.dbt_wcaldas.gold_document_periods`
where fiscal_period_method = 'ai'
order by doc_id;
