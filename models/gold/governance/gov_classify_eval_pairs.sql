-- Join chunk-majority classify labels to a human golden set (Meridian story docs).
-- Feeds package eval() — zero AI spend; scores prompt/taxonomy quality.
{{ config(materialized='table') }}

with chunk_labels as (
    select
        m.partition_key as doc_id,
        e.classification as predicted_label,
        count(*) as chunk_votes
    from {{ ref('documents_embedded_classified') }} e
    join {{ ref('documents_chunks_meta') }} m on m.chunk_id = e.chunk_id
    group by 1, 2
),

ranked as (
    select
        doc_id,
        predicted_label,
        chunk_votes,
        row_number() over (
            partition by doc_id
            order by chunk_votes desc, predicted_label
        ) as rn
    from chunk_labels
),

predicted as (
    select doc_id, predicted_label, chunk_votes
    from ranked
    where rn = 1
)

select
    g.doc_id,
    g.expected_label,
    p.predicted_label,
    p.chunk_votes,
    g.notes,
    case when p.predicted_label = g.expected_label then true else false end as is_correct
from {{ ref('eval_classify_golden') }} g
left join predicted p on p.doc_id = g.doc_id
