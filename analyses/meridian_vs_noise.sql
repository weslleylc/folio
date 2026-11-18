-- Contrast: Meridian (signal) vs other accounts (noise) in Gold rollups.
-- Exact-match SQL finds the account; context engineering finds the *meaning*.

select *
from {{ ref('gold_account_risk_rollup') }}
order by
    case when account_id = 'ACC-8847' then 0 else 1 end,
    covenant_docs desc,
    past_due_docs desc
