#!/usr/bin/env python3
"""Folio talk dashboard — Streamlit over BigQuery (or local DuckDB).

BigQuery (uses local SA JSON if present, or GOOGLE_APPLICATION_CREDENTIALS):
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
ASSETS = Path(__file__).resolve().parent / "assets"
DB_PATH = ROOT / "folio.duckdb"
DEFAULT_SA = ROOT / "roundtable-513102-545d77a8a510.json"

# Prefer explicit env, else local SA key (gitignored).
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and DEFAULT_SA.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(DEFAULT_SA)

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
      .decision-box {
        background: #fff; border: 1px solid #d7d0c3; border-radius: 12px;
        padding: 1rem 1.1rem; margin-bottom: 0.75rem;
      }
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
    from google.oauth2 import service_account

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and Path(creds_path).exists():
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        return bigquery.Client(project=BQ_PROJECT, credentials=credentials)
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


def show_asset(name: str, caption: str | None = None) -> None:
    path = ASSETS / name
    if path.exists():
        st.image(str(path), use_container_width=True, caption=caption)


# ---------------------------------------------------------------------------
st.sidebar.markdown("### Folio")
st.sidebar.caption("Medallion × context engineering · Meridian talk")
page = st.sidebar.radio(
    "Talk pages",
    [
        "D1 · Zero-copy vs physical copy",
        "D2 · Crawler vs event-driven",
        "D3 · Why not Bronze→Vector",
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
    sa = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    st.sidebar.caption("SA key · " + ("ok" if sa and Path(sa).exists() else "missing"))
else:
    st.sidebar.caption(f"DuckDB · `{DB_PATH.name}`")
if st.sidebar.button("Refresh data"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# ===========================================================================
if page == "D1 · Zero-copy vs physical copy":
    hero(
        "Decision — Zero-copy vs physical-copy Bronze",
        "From Beyond Tables: metadata-first Bronze with selective snapshots. Folio demo uses physical copy + seeds for Cloud simplicity.",
    )
    show_asset(
        "medallion-unstructured.png",
        "Medallion for unstructured data — Jojo Joseph, Beyond Tables",
    )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Zero-copy / metadata-only")
        st.markdown(
            """
            - Catalog: URI + MIME + sha256 + ACLs — **no binary duplicate**
            - Lower storage / egress; smaller attack surface
            - Simpler RTBF when source deletes the file
            - Fast time-to-catalog at petabyte scale
            - Tradeoff: re-parse hits source over the network; link rot / throttling
            """
        )
    with right:
        st.markdown("#### Physical copy / snapshot")
        st.markdown(
            """
            - Binaries land in a lakehouse landing zone
            - Quarantine / malware scan before Silver
            - Point-in-time audit if source overwrites/deletes
            - Tradeoff: storage sprawl, dual security perimeter
            """
        )

    st.markdown("#### Folio talk choice")
    st.info(
        "**Demo = physical-copy PDFs in git + `dbt seed` into BigQuery.** "
        "Production lean = metadata-only Bronze (`gs://…` URI + sha256) with selective snapshots "
        "for high-compliance records. Same catalog shape either way."
    )
    if table_exists("bronze_document_catalog"):
        st.subheader("Live catalog shape (demo)")
        st.dataframe(
            q(
                f"""
                select doc_id, uri, content_sha256, bronze_layer, mime_type, byte_size
                from {t('bronze_document_catalog')}
                order by effective_date
                """
            ),
            use_container_width=True,
            hide_index=True,
        )
    st.caption(
        "Source: [Beyond Tables…](https://jjojo.medium.com/beyond-tables-applying-the-medallion-architecture-to-unstructured-data-governance-39a81cfa3835)"
    )

# ===========================================================================
elif page == "D2 · Crawler vs event-driven":
    hero(
        "Decision — Active crawl vs event-driven discovery",
        "From Governing the Unstructured Enterprise Part 3: combine both — baseline crawl + continuous events.",
    )
    show_asset(
        "discovery-ingestion.png",
        "Data discovery & ingestion — Jojo Joseph, Part 3",
    )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Active crawling")
        st.markdown(
            """
            - Agent walks shares / buckets / libraries
            - **Complete inventory snapshot**
            - Heavy; can take days–weeks at scale
            - Only as current as last crawl finish
            """
        )
    with right:
        st.markdown("#### Event-driven (passive)")
        st.markdown(
            """
            - S3 events, SharePoint webhooks, audit logs
            - **Near-real-time** create/update discovery
            - Misses dark data never emitting events
            - Needs initial crawl as baseline
            """
        )

    st.success(
        "**Recommended pattern:** full crawl once → continuous event updates → "
        "periodic re-crawl to catch missed events. Folio skips connectors for the talk "
        "(seeded catalog); the decision still belongs on stage."
    )
    st.markdown(
        """
        Also decide **batch vs streaming** ingestion (Part 3 §3.4): daily batch is enough for most
        document estates; stream when sensitivity must restrict access immediately.
        """
    )
    st.caption(
        "Source: [Part 3 — Discovery & Ingestion](https://jjojo.medium.com/governing-the-unstructured-enterprise-part-3-03cc9ab06e83)"
    )

# ===========================================================================
elif page == "D3 · Why not Bronze→Vector":
    hero(
        "Anti-pattern — Bronze-to-Vector shortcut",
        "Skip Silver and you embed PII, boilerplate, and bad parses into the same index AI will trust.",
    )
    cols = st.columns(3)
    cols[0].markdown(
        """
        <div class="decision-box"><b>Bronze</b><br/>
        Provenance only — URI, hash, mime. No interpretation.</div>
        """,
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        """
        <div class="decision-box"><b>Silver gate</b><br/>
        Parse quality, sensitivity, quarantine — then promote.</div>
        """,
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        """
        <div class="decision-box"><b>Gold / context</b><br/>
        Facts + chunk → embed → classify → search under cost gates.</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        **Sound bite:** *Vectors without Silver are an ungoverned secondary store.*

        Folio enforces this: `silver_ready_documents` feeds chunking; AI models stay behind
        `ai_functions_enabled` + `guard_batch`.
        """
    )
    if table_exists("silver_document_bodies"):
        st.subheader("Silver statuses in this demo")
        st.bar_chart(
            q(
                f"""
                select silver_status, count(*) as docs
                from {t('silver_document_bodies')}
                group by 1
                """
            ).set_index("silver_status")
        )

# ===========================================================================
elif page == "1 · Gold rollup":
    hero(
        "Gold rollup — Meridian stands out",
        "Unstructured risk signals by account. Noise accounts keep naive search from being trivial.",
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

    st.subheader("Risk flags by account")
    st.bar_chart(rollup.set_index("account_name")[["covenant_docs", "liquidity_docs", "past_due_docs"]])
    st.dataframe(rollup, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "2 · Silver gate":
    hero(
        "Silver — quality & sensitivity before vectors",
        "Quarantine low-quality parses before any embedding spend.",
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
        st.bar_chart(silver.groupby("sensitivity_label").size().rename("docs"))

    st.dataframe(silver, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "3 · Search raw vs classified":
    hero(
        "Retrieval — cosine recall vs classification precision",
        "Same Meridian query. Raw cosine often surfaces boilerplate; taxonomy filter buys precision.",
    )
    if not table_exists("search"):
        st.warning(
            "No `search` table. Re-run:\n\n"
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
    st.bar_chart(compare.pivot_table(index="demo", columns="classification", values="hits", fill_value=0))
    st.subheader("Avg score by demo × classification")
    st.bar_chart(
        compare.pivot_table(index="demo", columns="classification", values="avg_score", fill_value=0)
    )
    demo_pick = st.selectbox("Show passages for", sorted(detail["demo"].unique()))
    st.dataframe(detail.loc[detail["demo"] == demo_pick], use_container_width=True, hide_index=True)

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
        "Cost gates + content_sha256 through chunks for purge/citation.",
    )
    left, right = st.columns(2)
    with left:
        st.subheader("AI spend")
        if table_exists("gov_ai_spend"):
            spend = q(
                f"""
                select function_name, model_name, row_count, est_tokens,
                       est_cost_usd, cost_source, completed, started_at
                from {t('gov_ai_spend')}
                order by started_at
                """
            )
            if spend.empty:
                st.info("No AI run events yet.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Runs", len(spend))
                c2.metric("Est. tokens", f"{float(spend['est_tokens'].fillna(0).sum()):,.0f}")
                c3.metric("Est. USD", f"${float(spend['est_cost_usd'].fillna(0).sum()):.5f}")
                by_fn = spend.groupby("function_name", as_index=False).agg(
                    tokens=("est_tokens", "sum"), cost_usd=("est_cost_usd", "sum")
                )
                st.bar_chart(by_fn.set_index("function_name")[["tokens", "cost_usd"]])
                st.dataframe(spend, use_container_width=True, hide_index=True)
        else:
            st.info("No gov_ai_spend yet.")

    with right:
        st.subheader("Meridian lineage (sha256)")
        if table_exists("gov_document_lineage"):
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
        else:
            st.info("No gov_document_lineage yet.")

# ===========================================================================
else:
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
    st.bar_chart(
        pd.DataFrame(
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
        ).set_index("stage")
    )
