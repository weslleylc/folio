.PHONY: pdfs extract deps build build-ai demo dashboard

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
	.venv/bin/streamlit run dashboard/app.py
