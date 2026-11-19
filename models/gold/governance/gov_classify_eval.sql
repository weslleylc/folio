-- dbt_context_engineering.eval() → accuracy / precision / recall (deterministic).
{{ config(materialized='table') }}

{{ dbt_context_engineering.eval(
    ref('gov_classify_eval_pairs'),
    'predicted_label',
    'expected_label',
    prompt_version='folio_content_type.v1'
) }}
