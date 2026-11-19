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

Sidebar pages (talk order):

**Decisions (article)**  
- D1 Zero-copy vs physical copy  
- D2 Crawler vs event-driven  
- D3 Why not Bronze→Vector  

**Live BigQuery marts**  
1. Gold rollup  
2. Silver gate  
3. Search raw vs classified  
4. Taxonomy  
5. Cost & lineage  
6. Overview  

Defaults: project `roundtable-513102`, dataset `dbt_wcaldas`  
Override: `FOLIO_BQ_PROJECT` / `FOLIO_BQ_DATASET`

Local DuckDB fallback: `make dashboard`
