-- 🥇 Gold: structured facts mined from Silver markdown (regex / SQL),
-- ready to join with warehouse tables. Lineage retained via doc_id + sha256.
{{ config(materialized='table') }}

with docs as (
    select * from {{ ref('silver_ready_documents') }}
),

signals as (
    select
        doc_id,
        account_id,
        doc_type,
        title,
        effective_date,
        sensitivity_label,
        content_sha256,
        citation_url,
        body_markdown,
        -- Lightweight structured extractions (deterministic demo signals).
        case
            when {{ folio_regexp_contains("lower(body_markdown)", "'past due|overdue|credit hold'") }}
                then true else false
        end as flag_past_due,
        case
            when {{ folio_regexp_contains("lower(body_markdown)", "'covenant|leverage ratio|event of default'") }}
                then true else false
        end as flag_covenant_language,
        case
            when {{ folio_regexp_contains("lower(body_markdown)", "'working capital|days sales outstanding|dso|liquidity'") }}
                then true else false
        end as flag_liquidity_language,
        case
            when {{ folio_regexp_contains("body_markdown", "'3\\.[0-9]{2}x'") }}
                then {{ folio_regexp_extract("body_markdown", "'(3\\.[0-9]{2})x'", 1) }}
        end as leverage_ratio_mention,
        case
            when {{ folio_regexp_contains("body_markdown", "'USD [0-9,]+'") }}
                then {{ folio_regexp_extract("body_markdown", "'USD ([0-9,]+(?:\\.[0-9]+)?)'", 1) }}
        end as first_usd_amount_raw
    from docs
)

select
    doc_id,
    account_id,
    doc_type,
    title,
    effective_date,
    sensitivity_label,
    content_sha256,
    citation_url,
    flag_past_due,
    flag_covenant_language,
    flag_liquidity_language,
    {{ folio_try_cast('leverage_ratio_mention', dbt.type_float()) }} as leverage_ratio_mention,
    {{ folio_try_cast("replace(first_usd_amount_raw, ',', '')", dbt.type_float()) }} as first_usd_amount,
    case
        when flag_covenant_language and flag_liquidity_language then 'high'
        when flag_covenant_language or flag_past_due or flag_liquidity_language then 'medium'
        else 'low'
    end as risk_signal_tier
from signals
