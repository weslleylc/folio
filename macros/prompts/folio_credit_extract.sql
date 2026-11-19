{#-
  Typed extraction for Meridian-style credit documents.
  Uses dbt_context_engineering.extract() — each fact carries an evidence quote
  so grounded() can fail hallucinated citations in CI.
-#}

{% macro prompt__folio_credit_extract__v1() -%}
{%- raw -%}
Extract structured credit-risk fields that are EXPLICITLY present in the document.
Do not invent numbers or names. If a field is absent, return an empty string for it.
Always include an evidence quote copied verbatim from the text.

primary_signal labels:
covenant_pressure — leverage covenants, amendments, headroom, event of default, credit committee
liquidity_stress — working capital, DSO, liquidity, cash conversion
collections_past_due — past due, overdue, credit hold, AP stretch
disclosure_only — public MD&A / earnings commentary without a clear risk action
none — no credit-risk signal

Document:
{{ input }}
{%- endraw -%}
{%- endmacro %}


{% macro schema__folio_credit_extract__v1() -%}
{%- raw -%}
{
  "type": "object",
  "properties": {
    "primary_signal": {
      "type": "string",
      "enum": [
        "covenant_pressure",
        "liquidity_stress",
        "collections_past_due",
        "disclosure_only",
        "none"
      ]
    },
    "leverage_mention": {
      "type": "string",
      "description": "Verbatim leverage figure if present (e.g. 3.55x), else empty"
    },
    "usd_amount_mention": {
      "type": "string",
      "description": "First USD amount mentioned if present, else empty"
    },
    "evidence": {
      "type": "string",
      "description": "Verbatim quote from the document supporting primary_signal"
    }
  },
  "required": ["primary_signal", "evidence"],
  "additionalProperties": false
}
{%- endraw -%}
{%- endmacro %}
