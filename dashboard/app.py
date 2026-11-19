#!/usr/bin/env python3
"""Folio talk dashboard — Streamlit over BigQuery (or local DuckDB).

BigQuery (default for the Cloud talk):
  gcloud auth application-default login
  make dashboard-bq

Local DuckDB:
  FOLIO_WAREHOUSE=duckdb make dashboard
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "folio.duckdb"

WAREHOUSE = os.environ.get("FOLIO_WAREHOUSE", "bigquery").strip().lower()
BQ_PROJECT = os.environ.get("FOLIO_BQ_PROJECT", "roundtable-513102")
BQ_DATASET = os.environ.get("FOLIO_BQ_DATASET", "dbt_wcaldas")

st.set_page_config(
    page_title="Folio · Meridian demo",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --ink: #1a2332;
        --panel: #ffffff;
        --muted: #5c6b7a;
        --line: #d7d0c3;
      }
      .stApp { background: linear-gradient(165deg, #e8eef2 0%, #f3efe6 45%, #efe6d8 100%); }
      h1, h2, h3 { color: var(--ink) !important; letter-spacing: -0.02em; }
      [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.75rem 1rem;
      }
      [data-testid="stSidebar"] { background: #15202b; }
      [data-testid="stSidebar"] * { color: #e8eef2 !important; }
      .folio-hero {
        font-family: "Iowan Old Style", "Palatino Linotype", Palatino, serif;
        font-size: 2.2rem; line-height: 1.1; margin-bottom: 0.2rem; color: #15202b;
      }
      .folio-sub { color: #5c6b7a; margin-bottom: 1.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def t(name: str) -> str:
    if WAREHOUSE == "bigquery":
        return f"`{BQ_PROJECT}.{BQ_DATASET}.{name}`"
    return name


@st.cache_resource
def bq_client():
    from google.cloud import bigquery

    return bigquery.Client(project=BQ_PROJECT)


@st.cache_resource
def duck_connect():
    import duckdb

    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}. Run `dbt build` first.")
        st.stop()
    return duckdb.connect(str(DB_PATH), read_only=True)


def q(sql: str) -> pd.DataFrame:
    if WAREHOUSE == "bigquery":
        return bq_client().query(sql).to_dataframe(create_bqstorage_client=False)
    return duck_connect().execute(sql).fetchdf()


def table_exists(name: str) -> bool:
    if WAREHOUSE == "bigquery":
        from google.cloud import bigquery

        sql = f"""
            select 1
            from `{BQ_PROJECT}.{BQ_DATASET}.INFORMATION_SCHEMA.TABLES`
            where table_name = @name
            limit 1
        """
        job = bq_client().query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("name", "STRING", name)]
            ),
        )
        return next(job.result(), None) is not None

    rows = duck_connect().execute(
        "select 1 from information_schema.tables where table_name = ? limit 1",
        [name],
    ).fetchall()
    return len(rows) > 0


def hero(title: str, sub: str) -> None:
    st.markdown(f'<div class="folio-hero">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="folio-sub">{sub}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
st.sidebar.markdown("### Folio")
st.sidebar.caption("Medallion × context engineering · Meridian talk")
page = st.sidebar.radio(
    "Talk pages",
    [
        "1 · Gold rollup",
        "2 · Silver gate",
        "3 · Search raw vs classified",
        "4 · Taxonomy",
        "5 · Cost & lineage",
        "Overview",
    ],
)
st.sidebar.markdown("---")
if WAREHOUSE == "bigquery":
    st.sidebar.caption(f"BigQuery · `{BQ_PROJECT}.{BQ_DATASET}`")
else:
    st.sidebar.caption(f"DuckDB · `{DB_PATH.name}`")
if st.sidebar.button("Refresh data"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# ===========================================================================
if page == "1 · Gold rollup":
    hero(
        "Gold rollup — Meridian stands out",
        "Unstructured risk signals by account. Noise accounts (BrightPeak, Summit) keep naive search from being trivial.",
    )
    if not table_exists("gold_account_risk_rollup"):
        st.error("Missing gold_account_risk_rollup — run dbt build on BigQuery.")
        st.stop()

    rollup = q(
        f"""
        select account_id, account_name, sector, document_count,
               past_due_docs, covenant_docs, liquidity_docs,
               max_leverage_mentioned, max_risk_tier, latest_doc_date
        from {t('gold_account_risk_rollup')}
        order by
          case max_risk_tier when 'high' then 3 when 'medium' then 2 when 'low' then 1 else 0 end desc,
          covenant_docs desc
        """
    )
    mer = rollup.loc[rollup["account_id"] == "ACC-8847"]
    c1, c2, c3, c4 = st.columns(4)
    if not mer.empty:
        m = mer.iloc[0]
        c1.metric("Meridian docs", int(m["document_count"]))
        c2.metric("Covenant docs", int(m["covenant_docs"]))
        c3.metric("Past-due docs", int(m["past_due_docs"]))
        c4.metric("Max risk tier", str(m["max_risk_tier"]))

    chart = rollup.set_index("account_name")[["covenant_docs", "liquidity_docs", "past_due_docs"]]
    st.subheader("Risk flags by account")
    st.bar_chart(chart)
    st.dataframe(rollup, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "2 · Silver gate":
    hero(
        "Silver — quality & sensitivity before vectors",
        "Quarantine low-quality parses before any embedding spend. Avoid the Bronze-to-vector shortcut.",
    )
    if not table_exists("silver_document_bodies"):
        st.error("Missing silver_document_bodies.")
        st.stop()

    silver = q(
        f"""
        select doc_id, account_id, doc_type, quality_score,
               sensitivity_label, silver_status, page_count
        from {t('silver_document_bodies')}
        order by quality_score
        """
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents", len(silver))
    c2.metric("Silver ready", int((silver["silver_status"] == "silver_ready").sum()))
    c3.metric("Avg quality", f"{silver['quality_score'].astype(float).mean():.2f}")

    left, right = st.columns(2)
    with left:
        st.subheader("Quality by doc")
        st.bar_chart(silver.set_index("doc_id")["quality_score"].astype(float))
    with right:
        st.subheader("Sensitivity mix")
        sens = silver.groupby("sensitivity_label").size().rename("docs")
        st.bar_chart(sens)

    st.dataframe(silver, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "3 · Search raw vs classified":
    hero(
        "Retrieval — cosine recall vs classification precision",
        "Same Meridian query. Raw cosine often surfaces boilerplate; taxonomy filter buys precision.",
    )
    if not table_exists("search"):
        st.warning(
            "No `search` table. Re-run on BigQuery:\n\n"
            "`dbt build --vars '{\"ai_functions_enabled\": true}'`"
        )
        st.stop()

    compare = q(
        f"""
        select demo, classification, count(*) as hits,
               avg(score) as avg_score, max(score) as max_score
        from {t('search')}
        group by 1, 2
        order by demo, hits desc
        """
    )
    detail = q(
        f"""
        select demo, source_id, classification, score, citation_url,
               substr(cast(text as string), 1, 180) as snippet
        from {t('search')}
        order by demo, score desc
        """
    )

    st.subheader("Hits by demo × classification")
    pivot = compare.pivot_table(
        index="demo", columns="classification", values="hits", fill_value=0
    )
    st.bar_chart(pivot)

    st.subheader("Avg score by demo × classification")
    pivot_score = compare.pivot_table(
        index="demo", columns="classification", values="avg_score", fill_value=0
    )
    st.bar_chart(pivot_score)

    demo_pick = st.selectbox("Show passages for", sorted(detail["demo"].unique()))
    st.dataframe(
        detail.loc[detail["demo"] == demo_pick],
        use_container_width=True,
        hide_index=True,
    )

# ===========================================================================
elif page == "4 · Taxonomy":
    hero(
        "Closed taxonomy — a product decision",
        "Labels in folio_content_type filter retrieval. Bad taxonomy quietly drops the right answer.",
    )
    if not table_exists("gov_classification_breakdown"):
        st.warning("Build AI layer first so gov_classification_breakdown exists.")
        st.stop()

    tax = q(
        f"""
        select classification, chunk_count, accounts, documents, avg_chunk_chars
        from {t('gov_classification_breakdown')}
        order by chunk_count desc
        """
    )
    if tax.empty:
        st.warning("No classified chunks yet.")
        st.stop()

    st.bar_chart(tax.set_index("classification")["chunk_count"])
    st.dataframe(tax, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "5 · Cost & lineage":
    hero(
        "Governed AI spend & RTBF lineage",
        "Cost gates (ai_functions_enabled, guard_batch) + content_sha256 through chunks for purge/citation.",
    )

    left, right = st.columns(2)

    with left:
        st.subheader("AI spend")
        if not table_exists("gov_ai_spend"):
            st.info("No gov_ai_spend yet.")
        else:
            spend = q(
                f"""
                select function_name, model_name, row_count, est_tokens,
                       est_cost_usd, cost_source, completed, started_at
                from {t('gov_ai_spend')}
                order by started_at
                """
            )
            if spend.empty:
                st.info("ai_run_log has no events yet.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Runs", len(spend))
                c2.metric("Est. tokens", f"{float(spend['est_tokens'].fillna(0).sum()):,.0f}")
                c3.metric("Est. USD", f"${float(spend['est_cost_usd'].fillna(0).sum()):.5f}")
                by_fn = spend.groupby("function_name", as_index=False).agg(
                    tokens=("est_tokens", "sum"),
                    cost_usd=("est_cost_usd", "sum"),
                )
                st.bar_chart(by_fn.set_index("function_name")[["tokens", "cost_usd"]])
                st.dataframe(spend, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Meridian lineage (sha256)")
        if not table_exists("gov_document_lineage"):
            st.info("No gov_document_lineage yet.")
        else:
            lin = q(
                f"""
                select doc_id, account_id, content_sha256, chunk_count,
                       lineage_status, sensitivity_label, risk_signal_tier
                from {t('gov_document_lineage')}
                where account_id = 'ACC-8847'
                order by doc_id
                """
            )
            st.dataframe(lin, use_container_width=True, hide_index=True)
            if not lin.empty:
                pick = st.selectbox("Drill doc", lin["doc_id"].tolist())
                row = lin.loc[lin["doc_id"] == pick].iloc[0]
                st.code(
                    f"content_sha256: {row['content_sha256']}\n"
                    f"chunks: {int(row['chunk_count'])}\n"
                    f"status: {row['lineage_status']}",
                    language="text",
                )

# ===========================================================================
else:  # Overview
    hero(
        "Governance overview",
        "Bronze → Silver → Gold + AI spend snapshot for the Meridian story.",
    )
    if not table_exists("gov_medallion_health"):
        st.warning("Missing gov_medallion_health.")
        st.stop()

    h = q(f"select * from {t('gov_medallion_health')}").iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bronze docs", int(h["bronze_docs"]))
    c2.metric("Silver ready %", f"{100 * float(h['pct_silver_ready'] or 0):.0f}%")
    c3.metric("Quarantined %", f"{100 * float(h['pct_quarantined'] or 0):.0f}%")
    c4.metric("Est. AI tokens", f"{int(h['ai_total_est_tokens']):,}")
    c5.metric("Est. AI cost", f"${float(h['ai_total_est_cost_usd']):.4f}")

    funnel = pd.DataFrame(
        {
            "stage": ["Bronze", "Silver bodies", "Silver ready", "Gold facts", "Hashed chunks"],
            "count": [
                int(h["bronze_docs"]),
                int(h["silver_docs"]),
                int(h["silver_ready"]),
                int(h["gold_fact_docs"]),
                int(h["hashed_chunks"]),
            ],
        }
    )
    st.bar_chart(funnel.set_index("stage"))
