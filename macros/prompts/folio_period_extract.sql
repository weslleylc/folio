{#-
  Hybrid extraction, step 2: fiscal period when the regex could not read it.
  Only documents with a quarter-like phrase the regex missed ever reach this prompt.
  Output is normalised ("2025" + "Q3") so it can be coalesced with the regex result.
-#}

{% macro prompt__folio_period_extract__v1() -%}
{%- raw -%}
Find the FISCAL PERIOD (year and quarter) that this document reports on or covers.
Rules:
- Fiscal year equals the calendar year; Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec.
- "quarter ended September 30, 2025" -> year 2025, quarter Q3.
- "third quarter of fiscal 2025" -> year 2025, quarter Q3.
- Only use a period that is EXPLICITLY stated. If none is stated, return empty strings.
- evidence must be copied verbatim from the text.

Document:
{{ input }}
{%- endraw -%}
{%- endmacro %}


{% macro schema__folio_period_extract__v1() -%}
{%- raw -%}
{
  "type": "object",
  "properties": {
    "fiscal_year": {
      "type": "string",
      "description": "Four-digit fiscal year (e.g. 2025), or empty if not stated"
    },
    "fiscal_quarter": {
      "type": "string",
      "enum": ["Q1", "Q2", "Q3", "Q4", ""]
    },
    "evidence": {
      "type": "string",
      "description": "Verbatim phrase from the document that states the period"
    }
  },
  "required": ["fiscal_year", "fiscal_quarter", "evidence"],
  "additionalProperties": false
}
{%- endraw -%}
{%- endmacro %}
