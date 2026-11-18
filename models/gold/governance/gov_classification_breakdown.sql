-- Classification distribution feeding retrieval precision (Gold / context).
-- Gated with the AI layer — needs documents_embedded_classified.
{{ config(
    materialized='table',
    enabled=var('ai_functions_enabled', false)
) }}

select
    classification,
    count(*) as chunk_count,
    count(distinct account_id) as accounts,
    count(distinct {{ folio_split_part('chunk_id', "'::'", 1) }}) as documents,
    avg(length(chunk_text)) as avg_chunk_chars
from {{ ref('documents_embedded_classified') }}
group by 1
