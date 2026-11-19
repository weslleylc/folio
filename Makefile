.PHONY: pdfs expand extract deps build build-ai demo dashboard dashboard-bq dashboard-warm

pdfs:
	.venv/bin/python scripts/generate_sample_pdfs.py

# ~100 PDFs + intentional quarantine hooks (Silver chart not all ready)
expand:
	.venv/bin/python scripts/expand_corpus.py 100

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

# Prefetch all Streamlit talk queries into dashboard/.cache (instant page flips)
dashboard-warm:
	FOLIO_WAREHOUSE=bigquery \
	FOLIO_BQ_PROJECT=$${FOLIO_BQ_PROJECT:-roundtable-513102} \
	FOLIO_BQ_DATASET=$${FOLIO_BQ_DATASET:-dbt_wcaldas} \
	GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS:-$(CURDIR)/roundtable-513102-545d77a8a510.json} \
	.venv/bin/python dashboard/data_cache.py --force

# Talk dashboard against dbt Cloud BigQuery marts (uses gitignored SA JSON if present)
dashboard-bq:
	FOLIO_WAREHOUSE=bigquery \
	FOLIO_BQ_PROJECT=$${FOLIO_BQ_PROJECT:-roundtable-513102} \
	FOLIO_BQ_DATASET=$${FOLIO_BQ_DATASET:-dbt_wcaldas} \
	GOOGLE_APPLICATION_CREDENTIALS=$${GOOGLE_APPLICATION_CREDENTIALS:-$(CURDIR)/roundtable-513102-545d77a8a510.json} \
	.venv/bin/streamlit run dashboard/app.py
