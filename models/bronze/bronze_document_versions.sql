-- 🥉 Bronze: APPEND-ONLY log of every file version ever registered (article §4).
--
-- Immutability rules (enforced, not just documented):
--   * rows are only ever INSERTED, never updated or deleted: 'append' where supported; on BigQuery
--     (no append strategy) a MERGE whose source already excludes existing keys — it can only insert.
--   * a row is identified by (doc_id, content_sha256); registering the same pair twice is a no-op.
--   * a changed file (same doc_id, new sha256) becomes bronze_version + 1; v1 stays forever.
--   * full_refresh is OFF unless allow_bronze_rebuild=true, so `dbt build --full-refresh`
--     cannot silently rewrite history.
--   * tests/assert_bronze_append_only.sql fails if versions are duplicated or have gaps.
--
-- Landing batches come from the raw_document_catalog seed (ingest_batch). Raise
-- bronze_max_batch to "receive" the next batch:  --vars '{"bronze_max_batch": 2}'
{{ config(
    materialized='incremental',
    incremental_strategy='merge' if target.type == 'bigquery' else 'append',
    unique_key=['doc_id', 'content_sha256'],
    full_refresh=var('allow_bronze_rebuild', false),
    docs={'node_color': '#CD7F32'}
) }}

with landed as (
    select
        doc_id,
        filename,
        relative_path,
        uri,
        doc_type,
        account_id,
        account_name,
        cast(effective_date as date) as effective_date,
        source_system,
        title,
        mime_type,
        cast(byte_size as {{ dbt.type_bigint() }}) as byte_size,
        content_sha256,
        cast(ingested_at as {{ dbt.type_timestamp() }}) as ingested_at,
        bronze_layer,
        cast(ingest_batch as {{ dbt.type_int() }}) as ingest_batch
    from {{ ref('raw_document_catalog') }}
    where cast(ingest_batch as {{ dbt.type_int() }}) <= {{ var('bronze_max_batch', 2) }}
),

new_rows as (
    select l.*
    from landed l
    {% if is_incremental() -%}
    where not exists (
        select 1
        from {{ this }} t
        where t.doc_id = l.doc_id
          and t.content_sha256 = l.content_sha256
    )
    {%- endif %}
)

select
    n.*,
    coalesce(prev.max_version, 0)
        + row_number() over (partition by n.doc_id order by n.ingest_batch, n.ingested_at) as bronze_version,
    {{ dbt.current_timestamp() }} as bronze_registered_at
from new_rows n
{% if is_incremental() -%}
left join (
    select doc_id, max(bronze_version) as max_version
    from {{ this }}
    group by 1
) prev on prev.doc_id = n.doc_id
{%- else -%}
left join (select cast(null as {{ dbt.type_string() }}) as doc_id, cast(null as {{ dbt.type_int() }}) as max_version) prev
    on prev.doc_id = n.doc_id
{%- endif %}
