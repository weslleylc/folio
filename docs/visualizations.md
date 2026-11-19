# Folio visualizations — Looker Studio

**Primary path for the talk:** Looker Studio on BigQuery marts.  
Step-by-step pages + custom SQL: **[`looker-studio.md`](looker-studio.md)**

| | |
|---|---|
| Project | `roundtable-513102` |
| Dataset | `dbt_wcaldas` |
| Report | 5 pages: Rollup → Silver → Search compare → Taxonomy → Cost/Lineage |
| Raw SQL backup | [`presentation_queries.sql`](presentation_queries.sql) in BigQuery Studio |

## Why Looker (for this talk)

- Shareable link / fullscreen — cleaner than clicking Studio charts live  
- Multi-chart pages (scorecards + bar + table) per beat  
- Same BigQuery tables you already built with dbt Cloud  

## Quick start

1. [lookerstudio.google.com](https://lookerstudio.google.com/) → Create report → BigQuery → **Custom query**
2. Follow [`looker-studio.md`](looker-studio.md) — add DS1…DS7, build 5 pages
3. Share → View → present

## Fallback

BigQuery Studio saved queries still work for Bronze catalog / narrative timeline tables if you don’t put those in Looker.
