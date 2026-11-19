-- 🥈 Silver: parsed, quality-scored, sanitized, version-stamped document text.
--
-- Article §5 (Silver gate), as implemented here:
--   1. Parse + OCR confidence  -> parse_status / quality_score  (quarantine)
--   2. PII detection           -> sensitivity_label + span redaction in body_sanitized
--   3. Sanitized view          -> body_sanitized is the ONLY text Gold may read
--   4. Duplicate resolution    -> identical sha256 seen earlier => quarantine_duplicate
--   5. Version stamp           -> silver_version_id (hash of extractor + sanitized text)
-- Only the CURRENT Bronze version of each document is read (older versions stay in Bronze).
-- Raw body_markdown stays here (Silver-restricted); downstream models read body_sanitized.
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
        cast(quality_score as {{ dbt.type_float() }}) as quality_score,
        sensitivity_label,
        {{ folio_try_cast('page_count', dbt.type_int()) }} as page_count,
        content_sha256,
        cast(extracted_at as timestamp) as extracted_at,
        -- Seeds store markdown as single-line with \n escapes (BigQuery CSV-safe).
        {{ folio_unescape_newlines('body_markdown') }} as body_markdown,
        citation_url
    from {{ ref('raw_document_bodies') }}
),

catalog as (
    select doc_id, content_sha256, filename, uri, byte_size, mime_type, ingested_at as bronze_ingested_at,
           bronze_version, n_bronze_versions
    from {{ ref('bronze_document_catalog') }}
),

sanitized as (
    select
        b.*,
        -- Span-level redaction: SSNs and e-mail addresses never leave Silver in clear text.
        {{ folio_regexp_replace(
            folio_regexp_replace('b.body_markdown', "'[0-9]{3}-[0-9]{2}-[0-9]{4}'", "'[REDACTED_SSN]'"),
            "'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}'",
            "'[REDACTED_EMAIL]'"
        ) }} as body_sanitized
    from bodies b
)

select
    s.doc_id,
    s.account_id,
    s.doc_type,
    s.title,
    s.effective_date,
    s.source_system,
    s.extractor,
    s.parse_status,
    s.quality_score,
    s.sensitivity_label,
    s.page_count,
    s.content_sha256,
    s.extracted_at,
    s.body_markdown,
    s.body_sanitized,
    s.body_markdown != s.body_sanitized as pii_redacted,
    -- Silver version: changes when the parser, the redaction rules or the text change.
    {{ dbt.hash(dbt.concat(['s.extractor', "'|'", 's.body_sanitized'])) }} as silver_version_id,
    s.citation_url,
    c.filename,
    c.uri as bronze_uri,
    c.byte_size,
    c.mime_type,
    c.bronze_version,
    c.n_bronze_versions,
    -- The Silver gate: first matching rule wins. Only 'silver_ready' flows to Gold + AI.
    case
        when s.parse_status = 'failed' then 'quarantine_parse_failed'
        when s.quality_score < 0.4 then 'quarantine_low_quality'
        when s.sensitivity_label = 'restricted_pii' then 'quarantine_pii_review'
        when row_number() over (
            partition by s.content_sha256
            order by c.bronze_ingested_at, s.doc_id
        ) > 1 then 'quarantine_duplicate'
        else 'silver_ready'
    end as silver_status
from sanitized s
join catalog c
    on c.doc_id = s.doc_id
   and c.content_sha256 = s.content_sha256
