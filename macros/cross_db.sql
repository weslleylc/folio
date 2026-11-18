{#-
  Thin adapter.dispatch helpers so Folio Gold/Silver SQL runs on DuckDB (local)
  and BigQuery (dbt Cloud) without dialect forks in every model.
-#}

{% macro folio_regexp_contains(expr, pattern) -%}
  {{ return(adapter.dispatch('folio_regexp_contains', 'folio')(expr, pattern)) }}
{%- endmacro %}

{% macro default__folio_regexp_contains(expr, pattern) -%}
  regexp_contains({{ expr }}, {{ pattern }})
{%- endmacro %}

{% macro duckdb__folio_regexp_contains(expr, pattern) -%}
  regexp_matches({{ expr }}, {{ pattern }})
{%- endmacro %}

{% macro bigquery__folio_regexp_contains(expr, pattern) -%}
  regexp_contains({{ expr }}, {{ pattern }})
{%- endmacro %}


{% macro folio_regexp_extract(expr, pattern, group=1) -%}
  {{ return(adapter.dispatch('folio_regexp_extract', 'folio')(expr, pattern, group)) }}
{%- endmacro %}

{% macro default__folio_regexp_extract(expr, pattern, group) -%}
  regexp_extract({{ expr }}, {{ pattern }}, {{ group }})
{%- endmacro %}

{% macro duckdb__folio_regexp_extract(expr, pattern, group) -%}
  regexp_extract({{ expr }}, {{ pattern }}, {{ group }})
{%- endmacro %}

{% macro bigquery__folio_regexp_extract(expr, pattern, group) -%}
  {#- BQ REGEXP_EXTRACT returns the first capturing group when the pattern has one. -#}
  regexp_extract({{ expr }}, {{ pattern }})
{%- endmacro %}


{% macro folio_try_cast(expr, data_type) -%}
  {{ return(adapter.dispatch('folio_try_cast', 'folio')(expr, data_type)) }}
{%- endmacro %}

{% macro default__folio_try_cast(expr, data_type) -%}
  try_cast({{ expr }} as {{ data_type }})
{%- endmacro %}

{% macro duckdb__folio_try_cast(expr, data_type) -%}
  try_cast({{ expr }} as {{ data_type }})
{%- endmacro %}

{% macro bigquery__folio_try_cast(expr, data_type) -%}
  safe_cast({{ expr }} as {{ data_type }})
{%- endmacro %}


{% macro folio_split_part(expr, delimiter, part) -%}
  {{ return(adapter.dispatch('folio_split_part', 'folio')(expr, delimiter, part)) }}
{%- endmacro %}

{% macro default__folio_split_part(expr, delimiter, part) -%}
  split_part({{ expr }}, {{ delimiter }}, {{ part }})
{%- endmacro %}

{% macro duckdb__folio_split_part(expr, delimiter, part) -%}
  split_part({{ expr }}, {{ delimiter }}, {{ part }})
{%- endmacro %}

{% macro bigquery__folio_split_part(expr, delimiter, part) -%}
  split({{ expr }}, {{ delimiter }})[safe_offset({{ (part | int) - 1 }})]
{%- endmacro %}


{% macro folio_strpos(haystack, needle) -%}
  {{ return(adapter.dispatch('folio_strpos', 'folio')(haystack, needle)) }}
{%- endmacro %}

{% macro default__folio_strpos(haystack, needle) -%}
  strpos({{ haystack }}, {{ needle }})
{%- endmacro %}

{% macro duckdb__folio_strpos(haystack, needle) -%}
  position({{ needle }} in {{ haystack }})
{%- endmacro %}

{% macro bigquery__folio_strpos(haystack, needle) -%}
  strpos({{ haystack }}, {{ needle }})
{%- endmacro %}


{% macro folio_date_trunc_day(expr) -%}
  {{ return(adapter.dispatch('folio_date_trunc_day', 'folio')(expr)) }}
{%- endmacro %}

{% macro default__folio_date_trunc_day(expr) -%}
  date_trunc('day', {{ expr }})
{%- endmacro %}

{% macro duckdb__folio_date_trunc_day(expr) -%}
  date_trunc('day', {{ expr }})
{%- endmacro %}

{% macro bigquery__folio_date_trunc_day(expr) -%}
  timestamp_trunc({{ expr }}, day)
{%- endmacro %}


{#- Seeds store markdown single-line with literal \n (BigQuery CSV-safe). -#}
{% macro folio_unescape_newlines(expr) -%}
  {{ return(adapter.dispatch('folio_unescape_newlines', 'folio')(expr)) }}
{%- endmacro %}

{% macro default__folio_unescape_newlines(expr) -%}
  replace({{ expr }}, '\\n', '\n')
{%- endmacro %}

{% macro duckdb__folio_unescape_newlines(expr) -%}
  {#- DuckDB does not treat \n as an escape inside ordinary string literals. -#}
  replace({{ expr }}, chr(92) || 'n', chr(10))
{%- endmacro %}

{% macro bigquery__folio_unescape_newlines(expr) -%}
  replace({{ expr }}, '\\n', '\n')
{%- endmacro %}
