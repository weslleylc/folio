{#-
  DuckDB has no native embed()/classify(). Stand-ins keep parsing green and
  let the DAG build locally with structurally compatible placeholder values.
-#}

{% macro ai_stand_in() -%}
    {{ return(target.type == 'duckdb') }}
{%- endmacro %}
