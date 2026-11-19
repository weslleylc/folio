{#-
  Version identity for the chunk classifier. Stored in documents_classify.classify_version so an
  incremental run re-labels a chunk only when its text, the prompt/schema version, or the model
  changes — never "just because dbt ran". Bump the prompt version in documents_classify.sql
  (and macros/prompts/folio_content_type.sql) to force a relabel.
-#}
{% macro folio_classify_version() -%}
    {{ return('folio_content_type.v1|' ~ var('model_classify')) }}
{%- endmacro %}


{#- Version identity for the fiscal-period AI fallback (see documents_period_fallback). -#}
{% macro folio_period_version() -%}
    {{ return('folio_period_extract.v1|' ~ var('model_extract', var('model_generate'))) }}
{%- endmacro %}
