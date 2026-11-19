"""Pre-fetch + disk cache for Folio Streamlit talk queries.

Warm once (make dashboard-warm or first Streamlit load), then pages read
local pickles — no BigQuery round-trips during the presentation.
"""

from __future__ import annotations

import hashlib
import os
import pickle
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
DEFAULT_SA = ROOT / "roundtable-513102-545d77a8a510.json"

WAREHOUSE = os.environ.get("FOLIO_WAREHOUSE", "bigquery").strip().lower()
BQ_PROJECT = os.environ.get("FOLIO_BQ_PROJECT", "roundtable-513102")
BQ_DATASET = os.environ.get("FOLIO_BQ_DATASET", "dbt_wcaldas")
DB_PATH = ROOT / "folio.duckdb"

# Prefer disk snapshots during the talk (set FOLIO_LIVE_QUERIES=1 to always hit WH).
USE_DISK = os.environ.get("FOLIO_LIVE_QUERIES", "").strip() not in {"1", "true", "yes"}

if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and DEFAULT_SA.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(DEFAULT_SA)


def t(name: str) -> str:
    if WAREHOUSE == "bigquery":
        return f"`{BQ_PROJECT}.{BQ_DATASET}.{name}`"
    return name


def _sql_key(sql: str) -> str:
    norm = " ".join(sql.split())
    return hashlib.sha1(f"{WAREHOUSE}|{BQ_DATASET}|{norm}".encode()).hexdigest()[:20]


def _cache_path(sql: str) -> Path:
    return CACHE_DIR / f"q_{_sql_key(sql)}.pkl"


def _table_cache_path(name: str) -> Path:
    return CACHE_DIR / f"exists_{WAREHOUSE}_{BQ_DATASET}_{name}.pkl"


def _bq_client():
    from google.cloud import bigquery
    from google.oauth2 import service_account

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        return bigquery.Client(project=BQ_PROJECT, credentials=credentials)
    return bigquery.Client(project=BQ_PROJECT)


def _duck():
    import duckdb

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=True)


def fetch_live(sql: str) -> pd.DataFrame:
    if WAREHOUSE == "bigquery":
        return _bq_client().query(sql).to_dataframe(create_bqstorage_client=False)
    return _duck().execute(sql).fetchdf()


def table_exists_live(name: str) -> bool:
    if WAREHOUSE == "bigquery":
        from google.cloud import bigquery

        sql = f"""
            select 1
            from `{BQ_PROJECT}.{BQ_DATASET}.INFORMATION_SCHEMA.TABLES`
            where table_name = @name
            limit 1
        """
        job = _bq_client().query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("name", "STRING", name)]
            ),
        )
        return next(job.result(), None) is not None

    rows = _duck().execute(
        "select 1 from information_schema.tables where table_name = ? limit 1",
        [name],
    ).fetchall()
    return len(rows) > 0


def q(sql: str, *, force_live: bool = False) -> pd.DataFrame:
    path = _cache_path(sql)
    if USE_DISK and not force_live and path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    df = fetch_live(sql)
    if USE_DISK:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
    return df


def table_exists(name: str, *, force_live: bool = False) -> bool:
    path = _table_cache_path(name)
    if USE_DISK and not force_live and path.exists():
        with path.open("rb") as f:
            return bool(pickle.load(f))
    exists = table_exists_live(name)
    if USE_DISK:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(exists, f, protocol=pickle.HIGHEST_PROTOCOL)
    return exists


def clear_disk_cache() -> int:
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for p in CACHE_DIR.glob("*.pkl"):
        p.unlink()
        n += 1
    meta = CACHE_DIR / "warm_meta.txt"
    if meta.exists():
        meta.unlink()
    return n


def cache_stats() -> dict:
    files = list(CACHE_DIR.glob("*.pkl")) if CACHE_DIR.exists() else []
    return {
        "dir": str(CACHE_DIR),
        "files": len(files),
        "use_disk": USE_DISK,
        "warmed": (CACHE_DIR / "warm_meta.txt").exists(),
    }


# Tables the talk pages check.
TALK_TABLES = [
    "bronze_document_catalog",
    "silver_document_bodies",
    "gold_account_risk_rollup",
    "gold_document_facts",
    "search",
    "gov_classification_breakdown",
    "gov_ai_spend",
    "gov_document_lineage",
    "documents_embed",
    "documents_extract_flat",
    "gov_classify_eval",
    "gov_classify_eval_pairs",
    "gov_medallion_health",
]


def talk_queries() -> dict[str, str]:
    """Named SQL used by Streamlit pages (pre-warm these)."""
    return {
        "corpus_counts": f"""
            select count(*) as docs,
                   count(distinct account_id) as accounts,
                   count(distinct doc_type) as doc_types
            from {t('bronze_document_catalog')}
        """,
        "bronze_catalog_sample": f"""
            select doc_id, uri, content_sha256, bronze_layer, mime_type, byte_size
            from {t('bronze_document_catalog')}
            order by effective_date
        """,
        "silver_status_counts": f"""
            select silver_status, count(*) as docs
            from {t('silver_document_bodies')}
            group by 1
        """,
        "gold_rollup": f"""
            select account_id, account_name, sector, document_count,
                   past_due_docs, covenant_docs, liquidity_docs,
                   max_leverage_mentioned, max_risk_tier, latest_doc_date
            from {t('gold_account_risk_rollup')}
            order by
              case max_risk_tier when 'high' then 3 when 'medium' then 2 when 'low' then 1 else 0 end desc,
              covenant_docs desc
        """,
        "gold_meridian_facts": f"""
            select doc_id, doc_type, title,
                   flag_past_due, flag_covenant_language, flag_liquidity_language,
                   leverage_ratio_mention, risk_signal_tier, effective_date
            from {t('gold_document_facts')}
            where account_id = 'ACC-8847'
            order by
              case risk_signal_tier when 'high' then 3 when 'medium' then 2 else 1 end desc,
              effective_date desc
        """,
        "silver_bodies": f"""
            select doc_id, account_id, doc_type, quality_score,
                   sensitivity_label, silver_status, page_count, parse_status
            from {t('silver_document_bodies')}
            order by quality_score
        """,
        "search_compare": f"""
            select demo,
                   count(*) as hits,
                   sum(case when account_key = 'ACC-8847' then 1 else 0 end) as meridian_hits,
                   sum(case when account_key != 'ACC-8847' then 1 else 0 end) as other_borrower_hits,
                   avg(score) as avg_score
            from {t('search')}
            group by 1
            order by demo
        """,
        "search_detail": f"""
            select demo, source_id, account_key, classification, round(score, 3) as score,
                   citation_url,
                   substr(replace(cast(text as string), '\\n', ' '), 1, 160) as snippet
            from {t('search')}
            order by demo, score desc
        """,
        "taxonomy": f"""
            select classification, chunk_count, accounts, documents, avg_chunk_chars
            from {t('gov_classification_breakdown')}
            order by chunk_count desc
        """,
        "ai_spend": f"""
            select function_name, model_name, row_count, est_tokens,
                   est_cost_usd, cost_source, completed, started_at
            from {t('gov_ai_spend')}
            order by started_at
        """,
        "meridian_lineage": f"""
            select doc_id, account_id, content_sha256, chunk_count,
                   lineage_status, sensitivity_label, risk_signal_tier
            from {t('gov_document_lineage')}
            where account_id = 'ACC-8847'
            order by doc_id
        """,
        "embed_stats": f"""
            select
              count(*) as chunks,
              count(distinct account_id) as accounts,
              max(embedding_dimension) as dims,
              min(model_version) as model_version
            from {t('documents_embed')}
        """,
        "embed_meridian_sample": f"""
            select chunk_id, account_id, doc_type, title,
                   embedding_dimension, model_version,
                   substr(cast(chunk_text as string), 1, 140) as chunk_preview,
                   content_hash
            from {t('documents_embed')}
            where account_id = 'ACC-8847'
            order by chunk_id
            limit 25
        """,
        "embed_by_account": f"""
            select account_id, count(*) as chunks
            from {t('documents_embed')}
            group by 1
            order by chunks desc
        """,
        "extract_flat": f"""
            select doc_id, doc_type, primary_signal,
                   leverage_mention, usd_amount_mention,
                   substr(cast(evidence as string), 1, 160) as evidence,
                   title
            from {t('documents_extract_flat')}
            order by primary_signal, doc_id
        """,
        "extract_vs_gold": f"""
            select
              sum(case when flag_covenant_language then 1 else 0 end) as gold_covenant,
              sum(case when flag_liquidity_language then 1 else 0 end) as gold_liquidity,
              sum(case when flag_past_due then 1 else 0 end) as gold_past_due
            from {t('gold_document_facts')}
            where account_id = 'ACC-8847'
        """,
        "classify_eval": f"""
            select metric, label, value
            from {t('gov_classify_eval')}
            order by metric, label
        """,
        "classify_eval_pairs": f"""
            select doc_id, expected_label, predicted_label, is_correct, chunk_votes, notes
            from {t('gov_classify_eval_pairs')}
            order by is_correct, doc_id
        """,
        "corpus_by_account": f"""
            select account_id, account_name, count(*) as docs
            from {t('bronze_document_catalog')}
            group by 1, 2
            order by docs desc
        """,
        "meridian_case": f"""
            select b.doc_id, b.doc_type, b.title, b.effective_date, s.silver_status
            from {t('bronze_document_catalog')} b
            join {t('silver_document_bodies')} s using (doc_id)
            where b.account_id = 'ACC-8847'
            order by b.effective_date
        """,
        "silver_quarantined": f"""
            select doc_id, account_id, parse_status, quality_score,
                   sensitivity_label, silver_status, title
            from {t('silver_document_bodies')}
            where silver_status != 'silver_ready'
            order by silver_status
        """,
        "gold_tier_counts": f"""
            select risk_signal_tier, count(*) as docs
            from {t('gold_document_facts')}
            group by 1
        """,
        "regex_vs_extract": f"""
            select g.doc_id, g.account_id, g.title,
                   g.risk_signal_tier as regex_tier,
                   g.flag_past_due, g.flag_covenant_language, g.flag_liquidity_language,
                   e.primary_signal as extract_signal,
                   substr(cast(e.evidence as string), 1, 200) as evidence,
                   case
                     when g.risk_signal_tier != 'low'
                          and e.primary_signal in ('none', 'disclosure_only') then 'regex false alarm'
                     when g.risk_signal_tier = 'low'
                          and e.primary_signal not in ('none', 'disclosure_only') then 'regex missed it'
                     else 'agree'
                   end as verdict
            from {t('gold_document_facts')} g
            join {t('documents_extract_flat')} e using (doc_id)
            order by verdict, g.doc_id
        """,
        "embed_neighbours": f"""
            with anchor as (
              select embedding as e from {t('documents_embed')}
              where chunk_id = 'MER-X01::1' limit 1
            )
            select d.chunk_id, d.account_id, d.doc_type,
                   round(1 - ML.DISTANCE(d.embedding, a.e, 'COSINE'), 3) as similarity,
                   substr(replace(cast(d.chunk_text as string), '\\n', ' '), 1, 110) as preview
            from {t('documents_embed')} d, anchor a
            order by similarity desc
            limit 10
        """,
        "embed_by_doc_type": f"""
            select doc_type, count(*) as chunks
            from {t('documents_embed')}
            group by 1
            order by chunks desc
        """,
        "lineage_status_counts": f"""
            select lineage_status, count(*) as docs
            from {t('gov_document_lineage')}
            group by 1
        """,
        "classify_samples": f"""
            select classification, chunk_id,
                   substr(replace(cast(chunk_text as string), '\\n', ' '), 1, 130) as preview
            from {t('documents_embedded_classified')}
            where account_id = 'ACC-8847' or classification = 'public_disclosure'
            qualify row_number() over (partition by classification order by chunk_id) <= 2
            order by classification, chunk_id
        """,
        "medallion_health": f"""
            select * from {t('gov_medallion_health')}
        """,
        # SQL talk pack (page 9)
        "pack_bronze": f"""
            select doc_id, doc_type, account_id, uri, content_sha256, bronze_layer
            from {t('bronze_document_catalog')}
            order by effective_date
            limit 20
        """,
        "pack_silver_status": f"""
            select silver_status, count(*) as docs
            from {t('silver_document_bodies')}
            group by 1
            order by docs desc
        """,
        "pack_gold_rollup": f"""
            select account_name, document_count, past_due_docs, covenant_docs,
                   liquidity_docs, max_risk_tier
            from {t('gold_account_risk_rollup')}
            order by covenant_docs desc
        """,
        "pack_embed": f"""
            select chunk_id, account_id, embedding_dimension, model_version,
                   substr(cast(chunk_text as string), 1, 100) as preview
            from {t('documents_embed')}
            where account_id = 'ACC-8847'
            limit 10
        """,
        "pack_extract": f"""
            select doc_id, primary_signal, leverage_mention, usd_amount_mention,
                   substr(cast(evidence as string), 1, 120) as evidence
            from {t('documents_extract_flat')}
            order by primary_signal
        """,
        "pack_search": f"""
            select demo, account_key, classification, round(score, 4) as score,
                   substr(replace(cast(text as string), '\\n', ' '), 1, 110) as snippet
            from {t('search')}
            order by demo, score desc
        """,
    }


def warm_talk_cache(*, force: bool = False, progress=None) -> dict:
    """Fetch every talk query + table_exists probe; write disk cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ok, skipped, errors = [], [], []

    tables = TALK_TABLES
    queries = talk_queries()
    total = len(tables) + len(queries)
    i = 0

    for name in tables:
        i += 1
        if progress:
            progress(i, total, f"table:{name}")
        try:
            if force:
                table_exists(name, force_live=True)
            else:
                table_exists(name)
            ok.append(f"table:{name}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"table:{name}: {exc}")

    for name, sql in queries.items():
        i += 1
        if progress:
            progress(i, total, name)
        path = _cache_path(sql)
        if path.exists() and not force:
            skipped.append(name)
            continue
        try:
            # Only run if table likely exists (cheap probe already cached)
            q(sql, force_live=True)
            ok.append(name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")

    meta = CACHE_DIR / "warm_meta.txt"
    meta.write_text(
        f"warehouse={WAREHOUSE}\ndataset={BQ_DATASET}\nok={len(ok)}\nskipped={len(skipped)}\nerrors={len(errors)}\n",
        encoding="utf-8",
    )
    return {"ok": ok, "skipped": skipped, "errors": errors, "dir": str(CACHE_DIR)}


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Warm Folio Streamlit query cache")
    p.add_argument("--force", action="store_true", help="Re-fetch even if cache exists")
    p.add_argument("--clear", action="store_true", help="Delete cache and exit")
    args = p.parse_args()
    if args.clear:
        n = clear_disk_cache()
        print(f"cleared {n} cache files")
        raise SystemExit(0)

    def _prog(i, total, label):
        print(f"[{i}/{total}] {label}")

    result = warm_talk_cache(force=args.force, progress=_prog)
    print(
        f"warmed → {result['dir']}  "
        f"ok={len(result['ok'])} skipped={len(result['skipped'])} errors={len(result['errors'])}"
    )
    for err in result["errors"]:
        print(f"  ERR {err}")
