-- End-to-end lineage: Bronze file → Silver parse → Gold fact → context chunks.
-- Supports "right to be forgotten" style drills: pick a doc_id / sha256 and
-- see every downstream artifact (article §6.2).
{{ config(materialized='table') }}

with bronze as (
    select
        doc_id,
        account_id,
        account_name,
        doc_type,
        source_system,
        title,
        filename,
        uri,
        content_sha256,
        byte_size,
        effective_date,
        ingested_at
    from {{ ref('bronze_document_catalog') }}
),

silver as (
    select
        doc_id,
        extractor,
        parse_status,
        quality_score,
        sensitivity_label,
        silver_status,
        extracted_at,
        citation_url
    from {{ ref('silver_document_bodies') }}
),

gold as (
    select
        doc_id,
        risk_signal_tier,
        flag_past_due,
        flag_covenant_language,
        flag_liquidity_language,
        leverage_ratio_mention
    from {{ ref('gold_document_facts') }}
),

chunks as (
    select
        partition_key as doc_id,
        count(*) as chunk_count,
        sum(length(chunk_text)) as chunk_chars
    from {{ ref('documents_hashed') }}
    group by 1
)

select
    b.doc_id,
    b.account_id,
    b.account_name,
    b.doc_type,
    b.source_system,
    b.title,
    b.filename,
    b.uri as bronze_uri,
    b.content_sha256,
    b.byte_size,
    b.effective_date,
    b.ingested_at,
    s.extractor,
    s.parse_status,
    s.quality_score,
    s.sensitivity_label,
    s.silver_status,
    s.extracted_at,
    s.citation_url,
    g.risk_signal_tier,
    g.flag_past_due,
    g.flag_covenant_language,
    g.flag_liquidity_language,
    g.leverage_ratio_mention,
    coalesce(c.chunk_count, 0) as chunk_count,
    coalesce(c.chunk_chars, 0) as chunk_chars,
    case
        when s.doc_id is null then 'bronze_only'
        when s.silver_status != 'silver_ready' then 'quarantined'
        when g.doc_id is null then 'silver_only'
        when coalesce(c.chunk_count, 0) = 0 then 'gold_no_chunks'
        else 'fully_promoted'
    end as lineage_status
from bronze b
left join silver s on s.doc_id = b.doc_id
left join gold g on g.doc_id = b.doc_id
left join chunks c on c.doc_id = b.doc_id
