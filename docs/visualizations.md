# Folio talk — BigQuery Studio only

Project: `roundtable-513102` · Dataset: `dbt_wcaldas`  
SQL: [`presentation_queries.sql`](presentation_queries.sql)

Open: [BigQuery Console](https://console.cloud.google.com/bigquery?project=roundtable-513102)

---

## Setup once (10 min)

1. In BigQuery Studio → **Query editor**.
2. For each block below: paste → **Run** → **Save query** with the exact name.
3. After Run, open **Chart** under the results and set the encoding (table below).
4. Leave the saved queries pinned / starred so the talk is: open → Run → Chart.

| Save as | Block in `presentation_queries.sql` | Result view |
|---|---|---|
| `folio_01_bronze` | 01 Bronze | **Table** (no chart) |
| `folio_02_silver` | 02 Silver | Bar |
| `folio_03_rollup` | 03 Gold rollup | Bar |
| `folio_04_facts` | 04 Gold facts | Table |
| `folio_05_timeline` | 05 Narrative | Table |
| `folio_06a_search_raw` | 06a Search raw | Bar |
| `folio_06b_search_classified` | 06b Search classified | Bar |
| `folio_06c_compare` | 06c Before/after | Stacked bar |
| `folio_07_taxonomy` | 07 Taxonomy | Pie |
| `folio_08_spend` | 08 AI spend | Bar |
| `folio_09_lineage` | 09 Lineage | Table |
| `folio_10_health` | 10 Medallion health | Table / scorecards |

### Chart encodings (Studio)

| Saved query | Chart | X / Dimension | Y / Metric | Notes |
|---|---|---|---|---|
| `folio_02_silver` | Bar | `doc_id` | `quality_score` | Optional color: `silver_status` |
| `folio_03_rollup` | Bar | `account_name` | `covenant_docs` | Add series for `past_due_docs` / `liquidity_docs` if UI allows |
| `folio_06a_search_raw` | Bar | `classification` | `score` | Or X=`source_id` for passage-level |
| `folio_06b_search_classified` | Bar | `classification` | `score` | Same axes as 06a — easy compare |
| `folio_06c_compare` | Stacked bar | `demo` | `hits` | Stack / series = `classification` |
| `folio_07_taxonomy` | Pie | `classification` | `chunk_count` | Closed taxonomy story |
| `folio_08_spend` | Bar | `function_name` | `est_cost_usd` | Or Y=`est_tokens` |

If Chart controls differ slightly in your UI: Dimension = category column, Measure = numeric column.

---

## Live talk click path (~12 min)

| Min | Open saved query | Say |
|---|---|---|
| 0 | `folio_01_bronze` | Hash + URI, no NLP. Seeds demo vs zero-copy prod. |
| 1 | `folio_02_silver` + chart | Quarantine / quality before any embed bill. |
| 3 | `folio_03_rollup` + chart | Meridian spike vs BrightPeak / Summit noise. |
| 5 | `folio_05_timeline` | Join ceiling — timeline yes, meaning no. |
| 7 | `folio_06a` then `folio_06b` | Raw recall vs classified precision. |
| 9 | `folio_06c` stacked | Same story in one chart. |
| 10 | `folio_07_taxonomy` pie | Taxonomy is a product decision. |
| 11 | `folio_08_spend` + `folio_09_lineage` | Cost gates + sha256 / RTBF. |

Skip `04` / `10` unless someone asks.

---

## Pre-flight (day of)

```text
[ ] AI build already ran (search + gov_classification_breakdown + gov_ai_spend populated)
[ ] Each folio_* query Runs without error
[ ] Charts still show after re-run (re-apply encoding if Studio resets)
[ ] Browser zoom ~110%, hide left nav if needed for projector
```

Re-check dataset name if you rebuilt under another dbt Cloud schema (`dbt_<user>`).
Update the `` `project.dataset` `` prefix in `presentation_queries.sql` if it changed.
