.PHONY: pdfs extract deps build build-ai demo dashboard dashboard-bq

pdfs:
	.venv/bin/python scripts/generate_sample_pdfs.py

extract:
	.venv/bin/python scripts/extract_with_docling.py

deps:
	.venv/bin/dbt deps

build:
	.venv/bin/dbt build

build-ai:
	.venv/bin/dbt build --vars '{"ai_functions_enabled": true}'

demo: build
	.venv/bin/python scripts/demo_queries.py

dashboard:
	FOLIO_WAREHOUSE=duckdb .venv/bin/streamlit run dashboard/app.py

# Talk dashboard against dbt Cloud BigQuery marts
dashboard-bq:
	FOLIO_WAREHOUSE=bigquery \
	FOLIO_BQ_PROJECT=$${FOLIO_BQ_PROJECT:-roundtable-513102} \
	FOLIO_BQ_DATASET=$${FOLIO_BQ_DATASET:-dbt_wcaldas} \
	.venv/bin/streamlit run dashboard/app.py
