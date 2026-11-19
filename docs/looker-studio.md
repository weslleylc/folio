# Folio talk — Looker Studio (BigQuery)

Project: `roundtable-513102` · Dataset: `dbt_wcaldas`  
Open: [Looker Studio](https://lookerstudio.google.com/)

Build a **5-page report**. Each page = one story beat. Share the link for the talk.

---

## 0. Create the report

1. **Create** → **Report**
2. When prompted for a data source: **BigQuery** → authorize with the same Google account that sees the project
3. Choose **Custom query** (not “My projects” table picker for the first source — easier to control)
4. Billing project: `roundtable-513102`
5. Paste the SQL for **Page 1** below → **Add** → **Add to report**
6. Rename the report: `Folio — Meridian governance demo`

You’ll add more data sources via **Resource → Manage added data sources → Add a data source**.

---

## Data sources (add these 6)

Name each source exactly so pages stay clear.

### DS1 — `folio_rollup`

```sql
select
  account_id,
  account_name,
  sector,
  document_count,
  past_due_docs,
  covenant_docs,
  liquidity_docs,
  max_leverage_mentioned,
  max_risk_tier,
  latest_doc_date
from `roundtable-513102.dbt_wcaldas.gold_account_risk_rollup`
```

### DS2 — `folio_silver`

```sql
select
  doc_id,
  account_id,
  doc_type,
  quality_score,
  sensitivity_label,
  silver_status,
  page_count
from `roundtable-513102.dbt_wcaldas.silver_document_bodies`
```

### DS3 — `folio_search_compare`

```sql
select
  demo,
  classification,
  count(*) as hits,
  avg(score) as avg_score,
  max(score) as max_score
from `roundtable-513102.dbt_wcaldas.search`
group by 1, 2
```

### DS4 — `folio_search_detail`

```sql
select
  demo,
  source_id,
  classification,
  score,
  citation_url,
  substr(text, 1, 200) as snippet
from `roundtable-513102.dbt_wcaldas.search`
```

### DS5 — `folio_taxonomy`

```sql
select
  classification,
  chunk_count,
  accounts,
  documents,
  avg_chunk_chars
from `roundtable-513102.dbt_wcaldas.gov_classification_breakdown`
```

### DS6 — `folio_spend`

```sql
select
  function_name,
  model_name,
  row_count,
  est_tokens,
  est_cost_usd,
  cost_source,
  completed,
  started_at
from `roundtable-513102.dbt_wcaldas.gov_ai_spend`
```

Optional 7th (lineage table page):

### DS7 — `folio_lineage`

```sql
select
  doc_id,
  account_id,
  content_sha256,
  chunk_count,
  lineage_status,
  sensitivity_label,
  risk_signal_tier
from `roundtable-513102.dbt_wcaldas.gov_document_lineage`
where account_id = 'ACC-8847'
```

After each custom query: **Add** → set **Field types** if Looker guesses wrong (`est_cost_usd` / `score` = Number, `started_at` = Date & Time).

---

## Pages (build in this order)

### Page 1 — Risk rollup (Meridian stands out)

- Data source: **DS1 `folio_rollup`**
- **Scorecards** (top row): `document_count` SUM, `covenant_docs` SUM, `past_due_docs` SUM  
  (or filter scorecards to `account_id = ACC-8847` with a filter control)
- **Bar chart**: Dimension `account_name` · Metrics `covenant_docs`, `liquidity_docs`, `past_due_docs`
- **Table**: all fields, sort by `max_risk_tier`
- Title: `Gold rollup — unstructured risk by account`

**Say:** Meridian vs noise accounts.

### Page 2 — Silver gate

- Data: **DS2 `folio_silver`**
- **Bar**: Dimension `doc_id` · Metric `quality_score` (AVG or none — already one row per doc; use MAX)
- **Pie** or bar: Dimension `sensitivity_label` · Metric `Record Count`
- **Table**: `doc_id`, `quality_score`, `sensitivity_label`, `silver_status`
- Title: `Silver — quality & sensitivity before vectors`

### Page 3 — Search raw vs classified (the aha)

- Data: **DS3 `folio_search_compare`**
- **Stacked bar**: Dimension `demo` · Breakdown dimension `classification` · Metric `hits`
- Optional second chart: Dimension `demo` · Metric `avg_score`
- Add a **filter control** on `demo` if you want to toggle
- Title: `Retrieval — cosine recall vs classification precision`

Also drop a **table** from **DS4 `folio_search_detail`** below (snippet + score), with filter `demo`.

### Page 4 — Taxonomy

- Data: **DS5 `folio_taxonomy`**
- **Donut / Pie**: Dimension `classification` · Metric `chunk_count`
- **Table**: all fields
- Title: `Closed taxonomy — product decision for precision`

### Page 5 — Cost gates + lineage

- Left: **DS6 `folio_spend`**
  - Scorecards: `est_tokens` SUM, `est_cost_usd` SUM
  - Bar: Dimension `function_name` · Metric `est_cost_usd` (SUM)
  - Table: run log
- Right / below: **DS7 `folio_lineage`** table (`content_sha256`, `chunk_count`, `lineage_status`)
- Title: `Governed AI spend & RTBF lineage`

---

## Talk mode

1. **Share** → anyone with link (or restricted to your org)
2. Open report → **View** (not Edit)
3. Present fullscreen (browser F11)
4. Page order = story: Rollup → Silver → Search → Taxonomy → Cost/Lineage

Keep BigQuery Studio open in another window only if you need raw SQL for Bronze/timeline (`presentation_queries.sql` 01 & 05).

---

## Pre-flight

```text
[ ] dbt AI build populated search, gov_classification_breakdown, gov_ai_spend
[ ] Each DS refreshes (Resource → Manage data sources → Edit → Refresh)
[ ] Bars show Meridian high on Page 1
[ ] Page 3 has two demos in the stacked bar
[ ] Share link opens without edit access for you on stage
```

If a chart is empty: the custom query returned 0 rows — re-run the AI dbt job, then **Refresh fields** on that data source.
