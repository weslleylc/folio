# Governance dashboard

Maps the [unstructured medallion article](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835) pillars onto Folio marts + Streamlit.

| Article pillar | Dashboard view | Mart |
|---|---|---|
| Cost & lifecycle efficiency | AI cost & tokens | `gov_ai_spend`, `gov_ai_spend_daily` |
| SLA / parse quality | Medallion health | `gov_medallion_health` |
| Privacy / sensitivity | Sensitivity & quality | `gov_sensitivity_breakdown` |
| End-to-end lineage / RTBF | Lineage & RTBF | `gov_document_lineage` |
| Governing AI consumers / precision | Retrieval taxonomy | `gov_classification_breakdown` |
| Stewardship queue | Sensitivity & quality → low quality | `silver_document_bodies` |

## Cost math

`ai_run_log.est_tokens` comes from the package (`log_ai_run` / `guard_batch`).  
`est_cost` is only filled by the package when `vars.cost_per_1k_tokens` is set. Folio keeps that null by default (safety), and `gov_ai_spend` applies `seeds/ref_ai_pricing.csv` demo rates so the dashboard still shows USD.

To log package-native cost on cloud runs:

```bash
dbt build --vars '{"ai_functions_enabled": true, "cost_per_1k_tokens": 0.00015}'
```

## Run

```bash
make dashboard
# opens Streamlit → Overview / AI cost / Medallion / Lineage / Sensitivity / Taxonomy
```
