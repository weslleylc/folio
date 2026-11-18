{#-
  Classify taxonomy for Folio financial documents.
  Filters semantic search toward the right document intent (covenant risk vs
  routine AP vs public disclosure, etc.).
-#}

{% macro prompt__folio_content_type__v1() -%}
{%- raw -%}
Classify the financial document text below into exactly one content-type label.

covenant_or_credit_risk: discusses leverage covenants, amendments, credit-committee
risk, headroom, events of default, or heightened monitoring of a borrower.
liquidity_or_working_capital: discusses cash, DSO/DPO, receivables aging, payables
stretch, free cash flow, or collections remediation.
supplier_collections: invoice / AP collections notices, past-due balances, credit holds,
or promise-to-pay language from a vendor perspective.
public_disclosure: SEC filing MD&A, earnings-call commentary intended for markets, or
similar public-company disclosure language.
routine_transaction: ordinary paid invoices, boilerplate facility language with no risk
signal, or unrelated healthy-borrower content.

Text:
{{ input }}
{%- endraw -%}
{%- endmacro %}


{% macro schema__folio_content_type__v1() -%}
{%- raw -%}
{
  "type": "object",
  "properties": {
    "content_type": {
      "type": "string",
      "enum": [
        "covenant_or_credit_risk",
        "liquidity_or_working_capital",
        "supplier_collections",
        "public_disclosure",
        "routine_transaction"
      ]
    }
  },
  "required": ["content_type"],
  "additionalProperties": false
}
{%- endraw -%}
{%- endmacro %}
