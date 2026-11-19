-- Bronze is append-only. Fails (returns rows) if the version log was rewritten:
--   * the same (doc_id, bronze_version) appears twice
--   * the same (doc_id, content_sha256) appears twice
--   * a document's versions are not 1..n without gaps
select doc_id, 'duplicate_version' as problem
from {{ ref('bronze_document_versions') }}
group by doc_id, bronze_version
having count(*) > 1

union all

select doc_id, 'duplicate_content' as problem
from {{ ref('bronze_document_versions') }}
group by doc_id, content_sha256
having count(*) > 1

union all

select doc_id, 'version_gap' as problem
from {{ ref('bronze_document_versions') }}
group by doc_id
having min(bronze_version) != 1 or max(bronze_version) != count(*)
