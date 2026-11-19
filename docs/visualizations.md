# Folio visualizations — Streamlit + BigQuery

Talk charts are built for you in Streamlit, reading the dbt Cloud dataset.

```bash
cd /Users/weslleylc/Documents/Projects/Blue\ Orange/folio
source .venv/bin/activate
pip install -r requirements.txt

# uses gitignored SA JSON in repo root (or set GOOGLE_APPLICATION_CREDENTIALS)
make dashboard-bq
# → http://localhost:8501
```

Sidebar pages (speaker order — see `docs/presentation.md`):

**Act I Problem** — 1 The problem · 2 The case: Meridian · 3 The approach  
**Act II Ingest** — 4 Bronze (zero-copy vs copy) · 5 Discovery (events vs crawler) · 6 Silver gate  
**Act III Structure** — 7 Gold flags · 8 Embeddings · 9 Taxonomy  
**Act IV Use it** — 10 Search raw vs filtered · 11 Extraction (regex vs `extract()`)  
**Act V Trust** — 12 Evals · 13 Cost & lineage · 14 Wrap-up  
**Appendix** — A SQL pack

Every chart has axis titles, value labels and a "How to read" box (axes → reading → so what).  
Queries are cached to disk: `make dashboard-warm` once, then page flips are instant.

Defaults: project `roundtable-513102`, dataset `dbt_wcaldas`  
Override: `FOLIO_BQ_PROJECT` / `FOLIO_BQ_DATASET`

Local DuckDB fallback: `make dashboard`
