#!/usr/bin/env python3
"""Folio Governance Dashboard — token cost, medallion health, lineage, privacy.

Run from the project root:
  streamlit run dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "folio.duckdb"

st.set_page_config(
    page_title="Folio Governance",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- visual system (avoid generic purple/cream AI defaults) ---
st.markdown(
    """
    <style>
      :root {
        --ink: #1a2332;
        --paper: #f3efe6;
        --panel: #ffffff;
        --accent: #0f6e56;
        --accent-2: #b45309;
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
      [data-testid="stSidebar"] {
        background: #15202b;
      }
      [data-testid="stSidebar"] * { color: #e8eef2 !important; }
      .folio-hero {
        font-family: "Iowan Old Style", "Palatino Linotype", Palatino, serif;
        font-size: 2.4rem; line-height: 1.1; margin-bottom: 0.2rem; color: #15202b;
      }
      .folio-sub { color: #5c6b7a; margin-bottom: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def connect() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}. Run `dbt build` first.")
        st.stop()
    return duckdb.connect(str(DB_PATH), read_only=True)


def q(sql: str) -> pd.DataFrame:
    return connect().execute(sql).fetchdf()


def table_exists(name: str) -> bool:
    rows = connect().execute(
        "select 1 from information_schema.tables where table_name = ? limit 1",
        [name],
    ).fetchall()
    return len(rows) > 0


# ---------------------------------------------------------------------------
st.sidebar.markdown("### Folio")
st.sidebar.caption("Unstructured medallion × context engineering")
page = st.sidebar.radio(
    "Views",
    [
        "Overview",
        "AI cost & tokens",
        "Medallion health",
        "Lineage & RTBF",
        "Sensitivity & quality",
        "Retrieval taxonomy",
    ],
)
st.sidebar.markdown("---")
st.sidebar.caption(f"DuckDB · `{DB_PATH.name}`")
if st.sidebar.button("Refresh data"):
    st.cache_resource.clear()
    st.rerun()

# ===========================================================================
if page == "Overview":
    st.markdown('<div class="folio-hero">Governance overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="folio-sub">Bronze provenance → Silver quality/privacy → Gold facts & '
        "AI spend — the checkpoints from unstructured medallion governance.</div>",
        unsafe_allow_html=True,
    )

    if not table_exists("gov_medallion_health"):
        st.warning("Build governance marts first: `dbt build -s governance`")
        st.stop()

    h = q("select * from gov_medallion_health").iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bronze docs", int(h["bronze_docs"]))
    c2.metric("Silver ready %", f"{100 * (h['pct_silver_ready'] or 0):.0f}%")
    c3.metric("Quarantined %", f"{100 * (h['pct_quarantined'] or 0):.0f}%")
    c4.metric("Est. AI tokens", f"{int(h['ai_total_est_tokens']):,}")
    c5.metric("Est. AI cost", f"${h['ai_total_est_cost_usd']:.4f}")

    left, right = st.columns(2)
    with left:
        st.subheader("Promotion funnel")
        funnel = pd.DataFrame(
            {
                "stage": ["Bronze catalog", "Silver bodies", "Silver ready", "Gold facts", "Hashed chunks"],
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

    with right:
        st.subheader("Risk signals in Gold")
        risk = pd.DataFrame(
            {
                "tier": ["high", "medium", "low"],
                "docs": [
                    int(h["gold_high_risk"]),
                    int(h["gold_medium_risk"]),
                    int(h["gold_low_risk"]),
                ],
            }
        )
        st.bar_chart(risk.set_index("tier"))

    st.subheader("Account risk rollup")
    st.dataframe(
        q(
            """
            select account_id, account_name, document_count, past_due_docs,
                   covenant_docs, liquidity_docs, max_leverage_mentioned, max_risk_tier
            from gold_account_risk_rollup
            order by case max_risk_tier when 'high' then 0 when 'medium' then 1 else 2 end,
                     document_count desc
            """
        ),
        use_container_width=True,
        hide_index=True,
    )

# ===========================================================================
elif page == "AI cost & tokens":
    st.markdown('<div class="folio-hero">AI cost & tokens</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="folio-sub">From <code>ai_run_log</code> (guard + audit) with '
        "dashboard pricing when <code>cost_per_1k_tokens</code> was unset.</div>",
        unsafe_allow_html=True,
    )

    if not table_exists("gov_ai_spend"):
        st.warning("No spend ledger yet. Run AI models then `dbt build -s gov_ai_spend+`.")
        st.stop()

    spend = q("select * from gov_ai_spend order by started_at desc")
    daily = q("select * from gov_ai_spend_daily order by spend_day, function_name")

    if spend.empty:
        st.info(
            "ai_run_log has no started events. Run "
            "`dbt build --vars '{ai_functions_enabled: true}'` then rebuild governance marts."
        )
        st.stop()

    total_tokens = float(spend["est_tokens"].fillna(0).sum())
    total_cost = float(spend["est_cost_usd"].fillna(0).sum())
    orphaned = int((~spend["completed"]).sum())
    runs = len(spend)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("AI runs", runs)
    c2.metric("Est. tokens", f"{total_tokens:,.0f}")
    c3.metric("Est. cost (USD)", f"${total_cost:.5f}")
    c4.metric("Orphaned starts", orphaned, help="started without matching completed")

    st.subheader("Spend by function")
    by_fn = (
        spend.groupby("function_name", as_index=False)
        .agg(tokens=("est_tokens", "sum"), cost_usd=("est_cost_usd", "sum"), runs=("invocation_id", "count"))
    )
    chart_col, table_col = st.columns([1.2, 1])
    with chart_col:
        st.bar_chart(by_fn.set_index("function_name")[["tokens", "cost_usd"]])
    with table_col:
        st.dataframe(by_fn, use_container_width=True, hide_index=True)

    st.subheader("Daily trend")
    if not daily.empty:
        trend = daily.groupby("spend_day", as_index=False).agg(
            tokens=("total_est_tokens", "sum"),
            cost_usd=("total_est_cost_usd", "sum"),
        )
        st.line_chart(trend.set_index("spend_day"))

    st.subheader("Run log detail")
    st.dataframe(
        spend[
            [
                "started_at",
                "function_name",
                "model_name",
                "node_id",
                "row_count",
                "est_tokens",
                "est_cost_usd",
                "cost_source",
                "completed",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("How cost is calculated"):
        st.markdown(
            """
            1. `log_ai_run` writes `est_tokens` before every AI call (package cost governance).
            2. If `vars.cost_per_1k_tokens` is set, the package also logs `est_cost`.
            3. Folio's `gov_ai_spend` fills gaps using `seeds/ref_ai_pricing.csv`
               (demo rates by function / model pattern) so the dashboard still works
               when the safety default leaves `est_cost` null.
            4. `guard_batch` blocks runs that would exceed `max_batch_rows` / `max_est_tokens`.
            """
        )
        if table_exists("ref_ai_pricing"):
            st.dataframe(q("select * from ref_ai_pricing"), use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "Medallion health":
    st.markdown('<div class="folio-hero">Medallion health</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="folio-sub">Coverage, parse quality, extractor mix, and SLA-ish freshness '
        "across Bronze → Silver → Gold.</div>",
        unsafe_allow_html=True,
    )

    h = q("select * from gov_medallion_health").iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Source systems", int(h["bronze_source_systems"]))
    c2.metric("Doc types", int(h["bronze_doc_types"]))
    c3.metric("Avg quality", f"{h['avg_quality_score']:.2f}")
    c4.metric("Min quality", f"{h['min_quality_score']:.2f}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Docling extracts", int(h["extracted_via_docling"]))
    c2.metric("Fallback extracts", int(h["extracted_via_fallback"]))
    c3.metric("Bronze bytes", f"{int(h['bronze_bytes']):,}")

    st.subheader("Freshness")
    st.write(
        {
            "bronze_last_ingest": str(h["bronze_last_ingest"]),
            "silver_last_extract": str(h["silver_last_extract"]),
            "snapshot_at": str(h["snapshot_at"]),
        }
    )

    st.subheader("Catalog by source system / type")
    st.dataframe(
        q(
            """
            select source_system, doc_type, count(*) as docs,
                   sum(byte_size) as bytes,
                   count(distinct account_id) as accounts
            from bronze_document_catalog
            group by 1, 2
            order by docs desc
            """
        ),
        use_container_width=True,
        hide_index=True,
    )

# ===========================================================================
elif page == "Lineage & RTBF":
    st.markdown('<div class="folio-hero">Lineage & right-to-be-forgotten</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="folio-sub">Every Gold fact and chunk retains Bronze <code>content_sha256</code>. '
        "Pick a document to see the purge surface.</div>",
        unsafe_allow_html=True,
    )

    lineage = q("select * from gov_document_lineage order by effective_date")
    status_counts = lineage["lineage_status"].value_counts().rename_axis("status").reset_index(name="docs")
    st.bar_chart(status_counts.set_index("status"))

    doc_ids = lineage["doc_id"].tolist()
    pick = st.selectbox("Document", doc_ids)
    row = lineage.loc[lineage["doc_id"] == pick].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Lineage status", row["lineage_status"])
    c2.metric("Chunks", int(row["chunk_count"]))
    c3.metric("Sensitivity", row["sensitivity_label"])

    st.code(
        f"""content_sha256: {row['content_sha256']}
bronze_uri:     {row['bronze_uri']}
citation_url:   {row['citation_url']}
risk_tier:      {row['risk_signal_tier']}
""",
        language="text",
    )

    st.subheader("Full lineage table")
    st.dataframe(
        lineage[
            [
                "doc_id",
                "account_id",
                "doc_type",
                "lineage_status",
                "sensitivity_label",
                "quality_score",
                "risk_signal_tier",
                "chunk_count",
                "content_sha256",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

# ===========================================================================
elif page == "Sensitivity & quality":
    st.markdown('<div class="folio-hero">Sensitivity & quality</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="folio-sub">Silver privacy tags and parse-quality gates before anything '
        "is embedded (avoid the Bronze-to-vector shortcut).</div>",
        unsafe_allow_html=True,
    )

    sens = q("select * from gov_sensitivity_breakdown order by document_count desc")
    left, right = st.columns(2)
    with left:
        st.subheader("By sensitivity label")
        by_label = sens.groupby("sensitivity_label", as_index=False)["document_count"].sum()
        st.bar_chart(by_label.set_index("sensitivity_label"))
    with right:
        st.subheader("By Silver status")
        by_status = sens.groupby("silver_status", as_index=False)["document_count"].sum()
        st.bar_chart(by_status.set_index("silver_status"))

    st.subheader("Quality distribution")
    st.dataframe(
        q(
            """
            select doc_id, account_id, doc_type, quality_score, sensitivity_label,
                   silver_status, extractor, parse_status
            from silver_document_bodies
            order by quality_score asc
            """
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Steward queue (low quality / quarantine)")
    steward = q(
        """
        select doc_id, title, quality_score, silver_status, sensitivity_label, extractor
        from silver_document_bodies
        where silver_status != 'silver_ready' or quality_score < 0.6
        order by quality_score
        """
    )
    if steward.empty:
        st.success("No documents in the steward queue.")
    else:
        st.dataframe(steward, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "Retrieval taxonomy":
    st.markdown('<div class="folio-hero">Retrieval taxonomy</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="folio-sub">Classification mix that filters semantic search — '
        "precision governance on top of embedding recall.</div>",
        unsafe_allow_html=True,
    )

    if not table_exists("gov_classification_breakdown"):
        st.info(
            "Classification breakdown builds with the AI layer. Run:\n\n"
            "`dbt build --vars '{ai_functions_enabled: true}' -s documents_embedded_classified gov_classification_breakdown`"
        )
        st.stop()

    breakdown = q("select * from gov_classification_breakdown order by chunk_count desc")
    if breakdown.empty:
        st.warning("No classified chunks yet.")
        st.stop()

    st.bar_chart(breakdown.set_index("classification")["chunk_count"])
    st.dataframe(breakdown, use_container_width=True, hide_index=True)

    if table_exists("search"):
        st.subheader("Latest search demo rows")
        st.dataframe(
            q(
                """
                select demo, source_id, classification, round(score, 3) as score,
                       left(text, 120) as snippet
                from search
                order by demo, score desc
                limit 40
                """
            ),
            use_container_width=True,
            hide_index=True,
        )
