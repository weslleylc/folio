# Folio visualizations for the talk

You already have the marts in BigQuery (`roundtable-513102.dbt_wcaldas`).  
Use **BigQuery Studio charts for live clicks** and **Looker Studio for 3–4 slides**.

Queries: [`presentation_queries.sql`](presentation_queries.sql).

---

## Option A — BigQuery Studio (fastest for live demo)

1. Open [BigQuery Studio](https://console.cloud.google.com/bigquery?project=roundtable-513102).
2. Paste a block from `presentation_queries.sql` → **Run**.
3. Under the results grid, open **Chart** / **Visualization**:

| Query | Chart type | Encoding |
|---|---|---|
| 02 Silver | Bar | X=`doc_id`, Y=`quality_score` |
| 03 Gold rollup | Bar | X=`account_name`, Y=`covenant_docs` (color=`max_risk_tier` if available) |
| 06a / 06b Search | Bar | X=`classification` or `source_id`, Y=`score` |
| 06c Before/after | Stacked bar | X=`demo`, stack=`classification`, Y=`hits` |
| 07 Taxonomy | Pie | Dimension=`classification`, metric=`chunk_count` |
| 08 Spend | Bar | X=`function_name`, Y=`est_cost_usd` |

4. **Save** each SQL as a saved query (`01_bronze`, `03_rollup`, …) so the talk is click → run → chart.

No extra product. Works offline-ish once results are cached in the tab.

---

## Option B — Looker Studio (best for slides / share link)

1. [Looker Studio](https://lookerstudio.google.com/) → **Create** → **Data source** → **BigQuery**.
2. Pick project `roundtable-513102`, dataset `dbt_wcaldas`.
3. Add these tables as separate data sources (or one custom query each):

| Page | Data source | Viz |
|---|---|---|
| Risk rollup | `gold_account_risk_rollup` | Bar: account vs covenant/liquidity/past_due |
| Silver gate | `silver_document_bodies` | Bar: quality_score; optional filter on `silver_status` |
| Search compare | custom SQL = query **06c** | Stacked bar demo × classification |
| Taxonomy | `gov_classification_breakdown` | Pie |
| Cost | `gov_ai_spend` | Bar / scorecard on `est_cost_usd`, `est_tokens` |
| Health | `gov_medallion_health` | Scorecards |

4. Share the report link; open fullscreen during Q&A.

**Custom query tip:** in the data source, choose **Custom query** and paste 06c / 08 so you don’t expose every column.

---

## Option C — Streamlit (local DuckDB only)

```bash
dbt build   # local DuckDB
make dashboard
```

Good for a laptop-only rehearsal. It does **not** read BigQuery unless you rewire `dashboard/app.py` to BQ. For the Cloud talk, prefer A or B.

---

## Suggested slide / tab order

1. Table: Bronze catalog (hash + URI)  
2. Chart: Silver quality  
3. Chart: Gold rollup (Meridian spike)  
4. Table: Narrative timeline  
5. Charts: Search raw vs classified (06a then 06b, or 06c)  
6. Pie: Taxonomy  
7. Chart + table: Spend + lineage  

---

## Pre-talk checklist

- [ ] `dbt build --vars '{"ai_functions_enabled": true}'` succeeded (so `search`, `gov_classification_breakdown`, spend rows exist)  
- [ ] Saved queries 01–10 in BigQuery Studio  
- [ ] Looker report published (optional)  
- [ ] Confirm dataset name still `dbt_wcaldas` (dev schemas can change per user)  
