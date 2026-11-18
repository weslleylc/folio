-- Privacy / sensitivity distribution (Silver governance gate).
{{ config(materialized='table') }}

select
    sensitivity_label,
    silver_status,
    doc_type,
    count(*) as document_count,
    avg(quality_score) as avg_quality_score,
    sum(case when account_id = 'ACC-8847' then 1 else 0 end) as meridian_docs
from {{ ref('silver_document_bodies') }}
group by 1, 2, 3
