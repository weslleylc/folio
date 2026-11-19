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
      .teach {
        background: #15202b; color: #e8eef2; border-radius: 12px;
        padding: 1rem 1.15rem; margin: 0.5rem 0 1rem 0; line-height: 1.45;
      }
      .teach b { color: #f0c674; }
      .teach code { background: #243447; padding: 0.1rem 0.35rem; border-radius: 4px; }
      .legend-row { margin: 0.35rem 0; }
      .tier-high { color: #c0392b; font-weight: 700; }
      .tier-med { color: #d68910; font-weight: 700; }
      .tier-low { color: #1e8449; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def teach(html: str) -> None:
    """Talk callout — short 'what you're seeing' box for the presenter."""
    st.markdown(f'<div class="teach">{html}</div>', unsafe_allow_html=True)


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
        "0 · The problem",
        "0b · What Folio proves",
        "D1 · Zero-copy vs physical copy",
        "D2 · Crawler vs event-driven",
        "D3 · Why not Bronze→Vector",
        "1 · Gold rollup",
        "2 · Silver gate",
        "3 · Search raw vs classified",
        "4 · Taxonomy",
        "5 · Cost & lineage",
        "6 · Embeddings mart",
        "7 · Typed extraction",
        "8 · Evals & package",
        "9 · SQL talk pack",
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
if page == "0 · The problem":
    hero(
        "The problem — financial documents are not tables",
        "Credit risk lives in PDFs, emails, memos, and filings. Warehouses were built for rows.",
    )
    teach(
        "<b>Why this talk exists</b><br/>"
        "A single borrower (Meridian / ACC-8847) leaves signal across invoices, covenant amendments, "
        "credit-committee memos, earnings calls, and 10-Q MD&A. None of that lands as a clean fact table. "
        "Meanwhile AI can <i>read</i> that mess — so teams dump files into a vector DB and hope."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("#### What breaks in practice")
        st.markdown(
            """
            - **Scattered signal** — past-due on an invoice, headroom in a facility PDF, DSO on a call
            - **Noise** — dozens of healthy accounts bury Meridian in naive search
            - **Bad parses** — blank scans / OCR garbage become “trusted” context
            - **Spend without gates** — embed everything, including PII and boilerplate
            - **No citation path** — agent answers without `sha256` / URI / evidence quote
            """
        )
    with right:
        st.markdown("#### What “good” looks like")
        st.markdown(
            """
            1. **Bronze** — catalog provenance (URI, hash, mime), not interpretation
            2. **Silver** — parse + quality + sensitivity + **quarantine**
            3. **Gold** — deterministic SQL facts (regex flags) you can explain
            4. **Context engineering** — chunk → embed → classify → search under cost gates
            5. **Extract + eval** — typed fields with evidence; score taxonomy like any dbt test
            """
        )
    if table_exists("bronze_document_catalog"):
        c1, c2, c3 = st.columns(3)
        cat = q(
            f"""
            select count(*) as docs,
                   count(distinct account_id) as accounts,
                   count(distinct doc_type) as doc_types
            from {t('bronze_document_catalog')}
            """
        ).iloc[0]
        c1.metric("Corpus docs", int(cat["docs"]))
        c2.metric("Accounts", int(cat["accounts"]))
        c3.metric("Doc types", int(cat["doc_types"]))
    st.info(
        "Sound bite: *The warehouse finally got AI SQL functions. What it still lacks is the "
        "medallion + context-engineering pattern for unstructured finance.*"
    )

# ===========================================================================
elif page == "0b · What Folio proves":
    hero(
        "Folio in one diagram",
        "Medallion for unstructured + dbt_context_engineering on BigQuery — same project, two layers of truth.",
    )
    teach(
        "<b>Two Gold paths (and)</b><br/>"
        "• <b>Deterministic</b> — <code>gold_document_facts</code> regex flags (free, brittle, explainable)<br/>"
        "• <b>AI</b> — embed / classify / extract / search (billed, semantic, gated)<br/>"
        "The talk is not “replace SQL with RAG.” It’s govern both."
    )
    cols = st.columns(4)
    cols[0].markdown(
        '<div class="decision-box"><b>1. Ingest</b><br/>Bronze catalog + Silver parse gate</div>',
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        '<div class="decision-box"><b>2. Structure</b><br/>Gold flags + optional extract()</div>',
        unsafe_allow_html=True,
    )
    cols[2].markdown(
        '<div class="decision-box"><b>3. Retrieve</b><br/>embed → classify → vector_search</div>',
        unsafe_allow_html=True,
    )
    cols[3].markdown(
        '<div class="decision-box"><b>4. Prove</b><br/>eval / grounded / cost log</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        **Package capabilities you will see live** (`dbt_context_engineering`):

        | Capability | Folio model | Why it matters |
        |---|---|---|
        | `chunk` / `embed` | `documents_embed` | Meaning-searchable vectors with content_hash refresh |
        | `classify` | `documents_classify` | Taxonomy filter → precision |
        | `extract` | `documents_extract_flat` | Typed facts + evidence quote |
        | `vector_search` | `search` | Cosine retrieval with citations |
        | `eval` / `grounded` | `gov_classify_eval` | CI-able quality, not vibes |
        | `guard_batch` / `log_ai_run` | `gov_ai_spend` | Cost ceiling + ledger |
        """
    )

# ===========================================================================
elif page == "D1 · Zero-copy vs physical copy":
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
        teach(
            "Live check: if Silver only shows <code>silver_ready</code>, the gate looks fake. "
            "We keep a few bad scans so quarantine bars appear — those never reach Gold or embeddings."
        )
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
        "Gold rollup — how risk flags work",
        "Silver markdown → deterministic SQL regex → per-doc flags → account rollup. Meridian should tower over noise.",
    )
    teach(
        "<b>What “Gold risks” mean (not a credit score)</b><br/>"
        "Each <code>silver_ready</code> document is scanned with SQL for three phrases. "
        "Those booleans become a simple tier — then we count docs per account.<br/><br/>"
        "<span class='legend-row'>• <b>flag_past_due</b> — text mentions past due / overdue / credit hold</span><br/>"
        "<span class='legend-row'>• <b>flag_covenant_language</b> — covenant / leverage ratio / event of default</span><br/>"
        "<span class='legend-row'>• <b>flag_liquidity_language</b> — working capital / DSO / liquidity</span><br/><br/>"
        "<span class='tier-high'>high</span> = covenant <b>and</b> liquidity in the same doc · "
        "<span class='tier-med'>medium</span> = any one flag · "
        "<span class='tier-low'>low</span> = none<br/><br/>"
        "Talk point: Meridian’s story docs trip these flags on purpose; noise accounts stay clean so the chart is readable."
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

    st.subheader("How many risk-flagged docs per account?")
    st.caption(
        "Bars = document counts that matched each flag. Meridian should dominate; "
        "other accounts are corpus noise (mostly low / zero)."
    )
    st.bar_chart(rollup.set_index("account_name")[["covenant_docs", "liquidity_docs", "past_due_docs"]])

    if table_exists("gold_document_facts"):
        with st.expander("Open Meridian documents that tripped flags (didactic drill-down)", expanded=True):
            facts = q(
                f"""
                select doc_id, doc_type, title,
                       flag_past_due, flag_covenant_language, flag_liquidity_language,
                       leverage_ratio_mention, risk_signal_tier, effective_date
                from {t('gold_document_facts')}
                where account_id = 'ACC-8847'
                order by
                  case risk_signal_tier when 'high' then 3 when 'medium' then 2 else 1 end desc,
                  effective_date desc
                """
            )
            st.dataframe(facts, use_container_width=True, hide_index=True)
            if not facts.empty:
                high = int((facts["risk_signal_tier"] == "high").sum())
                med = int((facts["risk_signal_tier"] == "medium").sum())
                low = int((facts["risk_signal_tier"] == "low").sum())
                st.info(
                    f"Meridian fact docs → **{high} high** / **{med} medium** / **{low} low**. "
                    "A ‘high’ doc mentions both covenant pressure and liquidity/DSO language in one file."
                )

    st.subheader("Account rollup table")
    st.dataframe(rollup, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "2 · Silver gate":
    hero(
        "Silver gate — not everything is ready",
        "Quality + parse status decide who reaches Gold/vectors. Quarantine is the point of this chart.",
    )
    teach(
        "<b>How to read <code>silver_status</code></b><br/>"
        "<span class='legend-row'>• <b>silver_ready</b> — parse ok and quality ≥ 0.4 → may be chunked / embedded</span><br/>"
        "<span class='legend-row'>• <b>quarantine_low_quality</b> — body too thin / garbled (quality &lt; 0.4)</span><br/>"
        "<span class='legend-row'>• <b>quarantine_parse_failed</b> — extractor marked the file failed</span><br/><br/>"
        "If this chart were 100% ready, Silver would look like a no-op. "
        "The demo injects a few bad scans on purpose so the gate is visible."
    )
    if not table_exists("silver_document_bodies"):
        st.error("Missing silver_document_bodies.")
        st.stop()

    silver = q(
        f"""
        select doc_id, account_id, doc_type, quality_score,
               sensitivity_label, silver_status, page_count, parse_status
        from {t('silver_document_bodies')}
        order by quality_score
        """
    )
    ready = int((silver["silver_status"] == "silver_ready").sum())
    quar = len(silver) - ready
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Documents", len(silver))
    c2.metric("Silver ready", ready)
    c3.metric("Quarantined", quar)
    c4.metric("Avg quality", f"{silver['quality_score'].astype(float).mean():.2f}")

    left, right = st.columns(2)
    with left:
        st.subheader("Status mix (should NOT be all ready)")
        status_counts = (
            silver.groupby("silver_status").size().rename("docs").reset_index()
        )
        st.bar_chart(status_counts.set_index("silver_status"))
        if quar == 0:
            st.warning(
                "All docs are silver_ready — re-seed after `scripts/expand_corpus.py` "
                "+ `extract_with_docling.py` so quarantine hooks land in BigQuery."
            )
        else:
            st.success(f"{quar} doc(s) quarantined — gate is doing work.")
    with right:
        st.subheader("Sensitivity mix")
        st.caption("PII / confidential tags are governance labels; they do not equal quarantine by themselves.")
        st.bar_chart(silver.groupby("sensitivity_label").size().rename("docs"))

    with st.expander("Quarantined + lowest-quality docs", expanded=True):
        bad = silver.loc[silver["silver_status"] != "silver_ready"].copy()
        if bad.empty:
            bad = silver.nsmallest(8, "quality_score")
        st.dataframe(bad, use_container_width=True, hide_index=True)

    st.subheader("Full Silver table")
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
elif page == "6 · Embeddings mart":
    hero(
        "Embeddings mart — what a vector row looks like",
        "An embedding is a derived asset: text → float[] under a pinned model, with hashes for refresh.",
    )
    teach(
        "<b>How to read this table</b><br/>"
        "• <code>embedding</code> — vector from <code>AI.EMBED</code> / package <code>embed()</code> "
        "(similar meaning ⇒ nearby vectors)<br/>"
        "• <code>content_hash</code> — re-embed only when chunk text drifts<br/>"
        "• <code>embedding_fn_fingerprint</code> — model/config bump forces full refresh<br/>"
        "• <code>embedding_dimension</code> — observed length (e.g. 768 for text-embedding-005)<br/><br/>"
        "Talk point: vectors without Silver quarantine = ungoverned secondary store."
    )
    if not table_exists("documents_embed"):
        st.warning("Build AI layer: `dbt build --select path:models/context --vars '{\"ai_functions_enabled\": true}'`")
        st.stop()

    stats = q(
        f"""
        select
          count(*) as chunks,
          count(distinct account_id) as accounts,
          max(embedding_dimension) as dims,
          min(model_version) as model_version
        from {t('documents_embed')}
        """
    ).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Embedded chunks", int(stats["chunks"]))
    c2.metric("Accounts", int(stats["accounts"]))
    c3.metric("Dimensions", int(stats["dims"] or 0))
    c4.metric("Model", str(stats["model_version"]))

    st.subheader("Sample rows (Meridian) — text + vector metadata")
    sample = q(
        f"""
        select chunk_id, account_id, doc_type, title,
               embedding_dimension, model_version,
               substr(cast(chunk_text as string), 1, 140) as chunk_preview,
               content_hash
        from {t('documents_embed')}
        where account_id = 'ACC-8847'
        order by chunk_id
        limit 25
        """
    )
    st.dataframe(sample, use_container_width=True, hide_index=True)

    st.subheader("Chunks per account (who got embedded?)")
    by_acct = q(
        f"""
        select account_id, count(*) as chunks
        from {t('documents_embed')}
        group by 1
        order by chunks desc
        """
    )
    st.bar_chart(by_acct.set_index("account_id"))

    with st.expander("SQL — peek at the embedding column shape"):
        st.code(
            f"""select chunk_id, embedding_dimension, model_version,
       array_length(embedding) as observed_len,  -- BQ
       substr(chunk_text, 1, 80) as preview
from {BQ_PROJECT}.{BQ_DATASET}.documents_embed
where account_id = 'ACC-8847'
limit 10;""",
            language="sql",
        )

# ===========================================================================
elif page == "7 · Typed extraction":
    hero(
        "Typed extraction — facts with evidence quotes",
        "Package extract() pulls structured fields from Meridian docs. grounded() fails invented quotes.",
    )
    teach(
        "<b>extract vs classify vs Gold regex</b><br/>"
        "• <b>Gold regex</b> — free booleans (past_due / covenant / liquidity)<br/>"
        "• <b>classify</b> — one closed label per chunk (taxonomy filter for search)<br/>"
        "• <b>extract</b> — multi-field record (signal + leverage + USD + <code>evidence</code> quote)<br/><br/>"
        "Only Meridian silver_ready docs are extracted (cost gate). Evidence must appear in source text."
    )
    if not table_exists("documents_extract_flat"):
        st.warning(
            "Missing documents_extract_flat — rebuild AI path after adding extract models."
        )
        st.stop()

    flat = q(
        f"""
        select doc_id, doc_type, primary_signal,
               leverage_mention, usd_amount_mention,
               substr(cast(evidence as string), 1, 160) as evidence,
               title
        from {t('documents_extract_flat')}
        order by primary_signal, doc_id
        """
    )
    c1, c2 = st.columns(2)
    c1.metric("Extracted docs", len(flat))
    c2.metric("Signals ≠ none", int((flat["primary_signal"] != "none").sum()) if len(flat) else 0)

    left, right = st.columns(2)
    with left:
        st.subheader("primary_signal mix")
        st.bar_chart(flat.groupby("primary_signal").size().rename("docs"))
    with right:
        st.subheader("vs Gold regex (same borrower)")
        if table_exists("gold_document_facts"):
            compare = q(
                f"""
                select
                  countif(flag_covenant_language) as gold_covenant,
                  countif(flag_liquidity_language) as gold_liquidity,
                  countif(flag_past_due) as gold_past_due
                from {t('gold_document_facts')}
                where account_id = 'ACC-8847'
                """
            )
            st.dataframe(compare, use_container_width=True, hide_index=True)
            st.caption("Gold = deterministic. Extract = model-typed + citable evidence.")

    st.subheader("Extraction mart")
    st.dataframe(flat, use_container_width=True, hide_index=True)

# ===========================================================================
elif page == "8 · Evals & package":
    hero(
        "Evals — treat AI like any other dbt object",
        "eval() scores classify vs a golden set. grounded() checks extract evidence. No vibes.",
    )
    teach(
        "<b>Package test trio (ADR-0007)</b><br/>"
        "• <code>eval</code> — accuracy / precision / recall vs golden labels (this page)<br/>"
        "• <code>grounded</code> — evidence quote ⊆ source text (on documents_extract_flat)<br/>"
        "• <code>conforms_to_schema</code> — label ∈ taxonomy enum<br/><br/>"
        "Also live in Folio: <code>guard_batch</code>, <code>log_ai_run</code>, "
        "<code>content_hash</code>, <code>vector_search</code>, <code>knowledge_base</code>."
    )

    if table_exists("gov_classify_eval"):
        metrics = q(
            f"""
            select metric, label, value
            from {t('gov_classify_eval')}
            order by metric, label
            """
        )
        overall = metrics.loc[
            (metrics["metric"] == "accuracy") & (metrics["label"] == "__overall__")
        ]
        if not overall.empty:
            st.metric("Classify accuracy (golden Meridian docs)", f"{float(overall.iloc[0]['value']):.0%}")
        st.subheader("eval() metrics")
        st.dataframe(metrics, use_container_width=True, hide_index=True)
        acc = metrics.loc[metrics["metric"] == "accuracy"]
        if not acc.empty:
            st.bar_chart(acc.set_index("label")["value"])
    else:
        st.warning("gov_classify_eval not built yet.")

    if table_exists("gov_classify_eval_pairs"):
        with st.expander("Golden pairs — predicted vs expected", expanded=True):
            pairs = q(
                f"""
                select doc_id, expected_label, predicted_label, is_correct, chunk_votes, notes
                from {t('gov_classify_eval_pairs')}
                order by is_correct, doc_id
                """
            )
            st.dataframe(pairs, use_container_width=True, hide_index=True)

    st.markdown(
        """
        **Presenter note:** Changing `folio_content_type` prompt/schema should move these metrics.
        That is the point — taxonomy is a product decision you can regression-test in CI.
        """
    )

# ===========================================================================
elif page == "9 · SQL talk pack":
    hero(
        "SQL talk pack — click-through in BigQuery Studio",
        "Same queries as docs/presentation_queries.sql. Run live; don’t paste secrets."
    )
    queries = [
        (
            "01 Bronze catalog",
            f"""select doc_id, doc_type, account_id, uri, content_sha256, bronze_layer
from `{BQ_PROJECT}.{BQ_DATASET}.bronze_document_catalog`
order by effective_date
limit 20;""",
        ),
        (
            "02 Silver status mix",
            f"""select silver_status, count(*) docs
from `{BQ_PROJECT}.{BQ_DATASET}.silver_document_bodies`
group by 1
order by docs desc;""",
        ),
        (
            "03 Gold rollup",
            f"""select account_name, document_count, past_due_docs, covenant_docs,
       liquidity_docs, max_risk_tier
from `{BQ_PROJECT}.{BQ_DATASET}.gold_account_risk_rollup`
order by covenant_docs desc;""",
        ),
        (
            "04 Embeddings sample",
            f"""select chunk_id, account_id, embedding_dimension, model_version,
       substr(chunk_text, 1, 100) preview
from `{BQ_PROJECT}.{BQ_DATASET}.documents_embed`
where account_id = 'ACC-8847'
limit 10;""",
        ),
        (
            "05 Extraction mart",
            f"""select doc_id, primary_signal, leverage_mention, usd_amount_mention,
       substr(evidence, 1, 120) evidence
from `{BQ_PROJECT}.{BQ_DATASET}.documents_extract_flat`
order by primary_signal;""",
        ),
        (
            "06 Classify eval",
            f"""select * from `{BQ_PROJECT}.{BQ_DATASET}.gov_classify_eval`
order by metric, label;

select doc_id, expected_label, predicted_label, is_correct
from `{BQ_PROJECT}.{BQ_DATASET}.gov_classify_eval_pairs`
order by is_correct, doc_id;""",
        ),
        (
            "07 Search demos",
            f"""select demo, classification, round(score, 4) score,
       substr(cast(text as string), 1, 120) snippet
from `{BQ_PROJECT}.{BQ_DATASET}.search`
order by demo, score desc;""",
        ),
    ]
    pick = st.selectbox("Query", [q[0] for q in queries])
    sql = dict(queries)[pick]
    st.code(sql, language="sql")
    if st.button("Run selected query"):
        try:
            # Support multi-statement by running first statement only for safety in UI
            first = sql.strip().split(";")[0] + ";"
            st.dataframe(q(first.rstrip(";")), use_container_width=True, hide_index=True)
            if sql.count(";") > 1:
                st.caption("UI runs the first statement; paste the full block in BigQuery Studio for both.")
        except Exception as exc:  # noqa: BLE001 — show warehouse errors to presenter
            st.error(str(exc))

# ===========================================================================
else:
    hero(
        "Governance overview",
        "Bronze → Silver → Gold + AI spend snapshot for the Meridian story.",
    )
    teach(
        "<b>One-slide story</b><br/>"
        "Bronze = cataloged files · Silver = parse + quarantine · Gold = risk flags rolled up by account · "
        "AI = embed/classify only on <code>silver_ready</code> under cost gates.<br/>"
        "Expect quarantined % &gt; 0 and Meridian dominating Gold covenant / past-due bars."
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
