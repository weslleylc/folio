-- Token-bounded chunks that never split a sentence or cross a document.
{{ config(materialized='table') }}

{{ dbt_context_engineering.chunk(
    relation=ref('split_documents'),
    id_column='sentence_id',
    order_column='sentence_index',
    text_column='sentence_text',
    partition_column='document_id'
) }}
