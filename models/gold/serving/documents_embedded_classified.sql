{{ config(materialized='table') }}

select
    e.*,
    c.content_type as classification
from {{ ref('documents_embed') }} e
join {{ ref('documents_classify') }} c on c.chunk_id = e.chunk_id
