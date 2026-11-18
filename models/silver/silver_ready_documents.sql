-- Silver documents that passed quality / parse gates — the only feed into
-- Gold structured facts and the context-engineering chunk pipeline.
{{ config(materialized='view') }}

select *
from {{ ref('silver_document_bodies') }}
where silver_status = 'silver_ready'
  and body_markdown is not null
  and length(trim(body_markdown)) > 0
