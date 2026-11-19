-- 🥇 Gold: one fiscal period per silver_ready document, resolved HYBRID:
--   1. regex           (free, deterministic)       -> method = 'regex'
--   2. AI extract()    (billed, only for the gap)  -> method = 'ai'
--   3. neither         (no period in the text)     -> method = 'not_found'
-- With ai_functions_enabled off, documents in the gap show 'pending_ai' instead.
{{ config(materialized='table') }}

with joined as (
    select
        g.doc_id,
        g.account_id,
        g.doc_type,
        g.title,
        g.period_hint,
        g.fiscal_period_regex,
        {% if var('ai_functions_enabled', false) -%}
        case
            when f.fiscal_year is not null and f.fiscal_year != ''
             and f.fiscal_quarter is not null and f.fiscal_quarter != ''
                then {{ dbt.concat(['f.fiscal_year', "'-'", 'f.fiscal_quarter']) }}
        end as fiscal_period_ai,
        f.evidence as ai_evidence,
        f.extract_text as ai_source_text
        {%- else -%}
        cast(null as {{ dbt.type_string() }}) as fiscal_period_ai,
        cast(null as {{ dbt.type_string() }}) as ai_evidence,
        cast(null as {{ dbt.type_string() }}) as ai_source_text
        {%- endif %}
    from {{ ref('gold_document_facts') }} g
    {% if var('ai_functions_enabled', false) -%}
    left join {{ ref('documents_period_fallback') }} f on f.doc_id = g.doc_id
    {%- endif %}
)

select
    doc_id,
    account_id,
    doc_type,
    title,
    period_hint,
    fiscal_period_regex,
    fiscal_period_ai,
    coalesce(fiscal_period_regex, fiscal_period_ai) as fiscal_period,
    case
        when fiscal_period_regex is not null then 'regex'
        when fiscal_period_ai is not null then 'ai'
        when period_hint {% if not var('ai_functions_enabled', false) %}then 'pending_ai'{% else %}then 'not_found'{% endif %}
        else 'not_found'
    end as fiscal_period_method,
    ai_evidence,
    ai_source_text
from joined
