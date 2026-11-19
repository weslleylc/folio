# Folio visualizations — Streamlit + BigQuery

Talk charts are built for you in Streamlit, reading the dbt Cloud dataset.

```bash
cd /Users/weslleylc/Documents/Projects/Blue\ Orange/folio
source .venv/bin/activate
pip install -r requirements.txt

# one-time: ADC for BigQuery
gcloud auth application-default login

make dashboard-bq
# → http://localhost:8501
```

Sidebar pages (talk order):

1. Gold rollup — Meridian vs noise  
2. Silver gate — quality / sensitivity  
3. Search raw vs classified  
4. Taxonomy  
5. Cost & lineage  
6. Overview  

Defaults: project `roundtable-513102`, dataset `dbt_wcaldas`  
Override: `FOLIO_BQ_PROJECT` / `FOLIO_BQ_DATASET`

Local DuckDB fallback: `make dashboard`
