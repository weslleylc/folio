-- Governance: AI token & cost ledger from dbt_context_engineering.ai_run_log.
-- Pairs started/completed events, fills est_cost from ref_ai_pricing when the
-- package left est_cost null (cost_per_1k_tokens unset — intentional safety default).
{# Build after the AI models when they are enabled, so the ledger is not empty on a one-shot build. #}
{% if var('embeddings_enabled', false) or var('ai_functions_enabled', false) %}
-- depends_on: {{ ref('documents_embed') }}
{% endif %}
{% if var('ai_functions_enabled', false) %}
-- depends_on: {{ ref('documents_classify') }}
-- depends_on: {{ ref('documents_extract') }}
-- depends_on: {{ ref('documents_period_fallback') }}
{% endif %}
{{ config(materialized='table', docs={'node_color': '#D4AF37'}) }}

with started as (
    select
        invocation_id,
        node_id,
        model_name,
        function_name,
        row_count,
        cast(est_tokens as {{ dbt.type_float() }}) as est_tokens,
        cast(est_cost as {{ dbt.type_float() }}) as logged_est_cost,
        run_at as started_at
    from {{ ref('ai_run_log') }}
    where event = 'started'
),

completed as (
    select
        invocation_id,
        node_id,
        function_name,
        run_at as completed_at
    from {{ ref('ai_run_log') }}
    where event = 'completed'
),

pricing as (
    select
        lower(trim(function_name)) as function_name,
        lower(trim(model_name_pattern)) as model_name_pattern,
        cast(cost_per_1k_tokens_usd as {{ dbt.type_float() }}) as cost_per_1k_tokens_usd,
        case
            when trim(model_name_pattern) = '*' then 2
            else 1
        end as match_priority
    from {{ ref('ref_ai_pricing') }}
),

matched_rate as (
    select
        s.invocation_id,
        s.node_id,
        s.function_name,
        p.cost_per_1k_tokens_usd,
        row_number() over (
            partition by s.invocation_id, s.node_id, s.function_name
            order by
                case when p.function_name = lower(s.function_name) then 0 else 1 end,
                p.match_priority,
                length(p.model_name_pattern) desc
        ) as rn
    from started s
    left join pricing p
        on (
            p.function_name = lower(s.function_name)
            or p.function_name = '*'
        )
       and (
            p.model_name_pattern = '*'
            or {{ folio_strpos("lower(coalesce(s.model_name, ''))", 'p.model_name_pattern') }} > 0
        )
),

best_rate as (
    select invocation_id, node_id, function_name, cost_per_1k_tokens_usd
    from matched_rate
    where rn = 1
)

select
    s.invocation_id,
    s.node_id,
    s.model_name,
    s.function_name,
    s.row_count,
    s.est_tokens,
    s.logged_est_cost,
    coalesce(
        s.logged_est_cost,
        s.est_tokens / 1000.0 * coalesce(r.cost_per_1k_tokens_usd, 0.0001)
    ) as est_cost_usd,
    s.started_at,
    c.completed_at,
    c.invocation_id is not null as completed,
    {{ folio_date_trunc_day('s.started_at') }} as spend_day,
    case
        when s.logged_est_cost is not null then 'package_logged'
        else 'dashboard_priced'
    end as cost_source
from started s
left join completed c
    on c.invocation_id = s.invocation_id
   and c.node_id = s.node_id
   and c.function_name = s.function_name
left join best_rate r
    on r.invocation_id = s.invocation_id
   and r.node_id = s.node_id
   and r.function_name = s.function_name
