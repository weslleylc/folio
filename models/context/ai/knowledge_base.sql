-- Cross-document knowledge base in the package common shape (ADR-0006).
-- Single source family today; add more relations here as new Docling feeds land.
{{ config(materialized='table', docs={'node_color': '#9B59B6'}) }}

{{ dbt_context_engineering.knowledge_base([
    {'relation': ref('documents_embedded_classified'), 'source_type': 'Financial Document',
     'source_id': 'chunk_id', 'account_key': 'account_id',
     'text': 'chunk_text', 'embedding': 'embedding', 'timestamp': 'artifact_ts',
     'citation_url': 'citation_url', 'classification': 'classification'}
]) }}
