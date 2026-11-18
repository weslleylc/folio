-- 🥇 Gold mart: per-account rollup of unstructured risk signals.
{{ config(materialized='table') }}

select
    a.account_id,
    a.account_name,
    a.sector,
    count(f.doc_id) as document_count,
    sum(case when f.flag_past_due then 1 else 0 end) as past_due_docs,
    sum(case when f.flag_covenant_language then 1 else 0 end) as covenant_docs,
    sum(case when f.flag_liquidity_language then 1 else 0 end) as liquidity_docs,
    max(f.leverage_ratio_mention) as max_leverage_mentioned,
    max(f.effective_date) as latest_doc_date,
    case max(case f.risk_signal_tier
            when 'high' then 3 when 'medium' then 2 when 'low' then 1 else 0 end)
        when 3 then 'high'
        when 2 then 'medium'
        when 1 then 'low'
    end as max_risk_tier
from {{ ref('dim_accounts') }} a
left join {{ ref('gold_document_facts') }} f
    on f.account_id = a.account_id
group by 1, 2, 3
