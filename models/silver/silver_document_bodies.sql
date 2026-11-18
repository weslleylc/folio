-- 🥈 Silver: parsed, quality-scored, sensitivity-tagged document text.
-- Docling cracked the PDF into markdown; this model enforces Silver gates
-- (quality threshold, parse_status) before Gold / context engineering.
{{ config(materialized='table') }}

with bodies as (
    select
        doc_id,
        account_id,
        doc_type,
        title,
        cast(effective_date as date) as effective_date,
        source_system,
        extractor,
        parse_status,
        cast(quality_score as double) as quality_score,
        sensitivity_label,
        {{ folio_try_cast('page_count', dbt.type_int()) }} as page_count,
        content_sha256,
        cast(extracted_at as timestamp) as extracted_at,
        body_markdown,
        citation_url
    from {{ ref('raw_document_bodies') }}
),

catalog as (
    select doc_id, filename, uri, byte_size, mime_type
    from {{ ref('bronze_document_catalog') }}
)

select
    b.*,
    c.filename,
    c.uri as bronze_uri,
    c.byte_size,
    c.mime_type,
    case
        when b.parse_status = 'failed' then 'quarantine_parse_failed'
        when b.quality_score < 0.4 then 'quarantine_low_quality'
        else 'silver_ready'
    end as silver_status
from bodies b
join catalog c on c.doc_id = b.doc_id
