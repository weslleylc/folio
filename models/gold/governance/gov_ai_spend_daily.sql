-- Daily rollup of AI spend for the cost dashboard.
{{ config(materialized='table') }}

select
    spend_day,
    function_name,
    model_name,
    count(*) as runs,
    sum(case when completed then 1 else 0 end) as completed_runs,
    sum(case when not completed then 1 else 0 end) as orphaned_starts,
    sum(coalesce(row_count, 0)) as total_rows,
    sum(coalesce(est_tokens, 0)) as total_est_tokens,
    sum(coalesce(est_cost_usd, 0)) as total_est_cost_usd,
    avg(est_tokens) as avg_tokens_per_run,
    avg(est_cost_usd) as avg_cost_per_run
from {{ ref('gov_ai_spend') }}
group by 1, 2, 3
