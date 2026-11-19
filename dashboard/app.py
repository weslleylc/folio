#!/usr/bin/env python3
"""Folio talk dashboard — Streamlit over BigQuery (or local DuckDB).

BigQuery (uses local SA JSON if present, or GOOGLE_APPLICATION_CREDENTIALS):
  make dashboard-bq

Local DuckDB:
  FOLIO_WAREHOUSE=duckdb make dashboard

Page order = speaker order (docs/presentation.md). Every chart sits under a
"How to read this chart" box: axes -> reading -> so what.
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / "assets"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from glossary import CREDIT_TERMS, LABELS, PIPELINE_TERMS, as_markdown
from data_cache import (  # noqa: E402
    BQ_DATASET,
    BQ_PROJECT,
    WAREHOUSE,
    cache_stats,
    clear_disk_cache,
    q,
    table_exists,
    talk_queries,
    warm_talk_cache,
)

MERIDIAN = "ACC-8847"
GREEN, RED, AMBER, BLUE, GREY = "#1e8449", "#c0392b", "#d68910", "#2e6da4", "#9aa5b1"

st.set_page_config(
    page_title="Folio · Meridian demo",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load(name: str) -> pd.DataFrame:
    """Named talk query — hits disk cache after `make dashboard-warm`."""
    return q(talk_queries()[name])


st.markdown(
    """
    <style>
      :root { --ink:#1a2332; --panel:#ffffff; --muted:#5c6b7a; --line:#d7d0c3; }
      .stApp { background: linear-gradient(165deg, #e8eef2 0%, #f3efe6 45%, #efe6d8 100%); }
      h1, h2, h3 { color: var(--ink) !important; letter-spacing: -0.02em; }
      [data-testid="stMetric"] {
        background: var(--panel); border: 1px solid var(--line);
        border-radius: 12px; padding: 0.75rem 1rem;
      }
      [data-testid="stSidebar"] { background: #15202b; }
      [data-testid="stSidebar"] * { color: #e8eef2 !important; }
      .folio-hero {
        font-family: "Iowan Old Style", "Palatino Linotype", Palatino, serif;
        font-size: 2.1rem; line-height: 1.1; margin-bottom: 0.2rem; color: #15202b;
      }
      .folio-sub { color: #5c6b7a; margin-bottom: 1.1rem; font-size: 1.05rem; }
      .decision-box {
        background: #fff; border: 1px solid #d7d0c3; border-radius: 12px;
        padding: 1rem 1.1rem; margin-bottom: 0.75rem; min-height: 5.5rem;
      }
      .teach {
        background: #15202b; color: #e8eef2; border-radius: 12px;
        padding: 1rem 1.15rem; margin: 0.5rem 0 1rem 0; line-height: 1.5;
      }
      /* Force readable colours on every descendant: Streamlit's own markdown styles
         (theme text colour, code chips) otherwise override the box colours. */
      .teach, .teach * { color: #e8eef2 !important; }
      .teach b, .teach strong { color: #f0c674 !important; }
      .teach code { background: #2f4358 !important; color: #ffe9b0 !important;
                    padding: 0.1rem 0.35rem; border-radius: 4px; }
      .guide {
        background: #fffaf0; border-left: 5px solid #d68910; border-radius: 6px;
        padding: 0.7rem 1rem; margin: 0.25rem 0 0.75rem 0; line-height: 1.5; color: #1a2332;
      }
      .guide, .guide * { color: #1a2332 !important; }
      .guide b { color: #8a5a00 !important; }
      .guide code { background: #f3e3c0 !important; color: #1a2332 !important; }
      .decision-box, .decision-box * { color: #1a2332 !important; }
      .decision-box code { background: #eef1f4 !important; color: #1a2332 !important; }
      .question, .question * { color: #15202b !important; }
      .nextup, .nextup * { color: #5c6b7a !important; }
      .nextup b { color: #1a2332 !important; }
      .question {
        background: #fff; border: 2px solid #15202b; border-radius: 12px;
        padding: 1rem 1.2rem; font-size: 1.15rem; margin: 0.5rem 0 1rem 0; color: #15202b;
      }
      .nextup { color: #5c6b7a; margin-top: 1.5rem; padding-top: 0.6rem; border-top: 1px solid #d7d0c3; }
      .tier-high { color: #c0392b; font-weight: 700; }
      .tier-med { color: #d68910; font-weight: 700; }
      .tier-low { color: #1e8449; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def teach(html: str) -> None:
    st.markdown(f'<div class="teach">{html}</div>', unsafe_allow_html=True)


def guide(axes: str, reading: str, sowhat: str) -> None:
    """Chart-guide box: what the axes are, how to read it, why it matters."""
    st.markdown(
        '<div class="guide">'
        f"<b>Axes</b> — {axes}<br/>"
        f"<b>How to read</b> — {reading}<br/>"
        f"<b>So what</b> — {sowhat}"
        "</div>",
        unsafe_allow_html=True,
    )


def hero(title: str, sub: str) -> None:
    st.markdown(f'<div class="folio-hero">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="folio-sub">{sub}</div>', unsafe_allow_html=True)


def show_asset(name: str, caption: str | None = None) -> None:
    path = ASSETS / name
    if path.exists():
        st.image(str(path), width="stretch", caption=caption)


def card(title: str, body: str) -> str:
    return f'<div class="decision-box"><b>{title}</b><br/>{body}</div>'


def bar(
    df: pd.DataFrame,
    cat: str,
    val: str,
    *,
    title: str,
    cat_title: str,
    val_title: str,
    color: str | None = None,
    colors: dict | None = None,
    horizontal: bool = True,
    sort: str | list | None = "-x",
    height: int | None = None,
    fmt: str = ",.0f",
) -> None:
    """Altair bar with titled axes + value labels (no unlabeled st.bar_chart)."""
    if df.empty:
        st.info("No rows.")
        return
    base = alt.Chart(df)
    if horizontal:
        x = alt.X(f"{val}:Q", title=val_title)
        y = alt.Y(f"{cat}:N", title=cat_title, sort=sort)
    else:
        x = alt.X(f"{cat}:N", title=cat_title, sort=sort if sort != "-x" else None)
        y = alt.Y(f"{val}:Q", title=val_title)
    enc = {"x": x, "y": y}
    if color and colors:
        enc["color"] = alt.Color(
            f"{color}:N",
            scale=alt.Scale(domain=list(colors), range=list(colors.values())),
            legend=alt.Legend(title=None, orient="bottom"),
        )
        bars = base.mark_bar().encode(**enc, tooltip=list(df.columns))
    elif color:
        enc["color"] = alt.Color(f"{color}:N", legend=alt.Legend(title=None, orient="bottom"))
        bars = base.mark_bar().encode(**enc, tooltip=list(df.columns))
    else:
        bars = base.mark_bar(color=BLUE).encode(**enc, tooltip=list(df.columns))
    text = base.mark_text(
        align="left" if horizontal else "center",
        baseline="middle" if horizontal else "bottom",
        dx=4 if horizontal else 0,
        dy=0 if horizontal else -2,
        color="#1a2332",
    ).encode(
        x=x if horizontal else alt.X(f"{cat}:N", sort=sort if sort != "-x" else None),
        y=y if horizontal else alt.Y(f"{val}:Q"),
        text=alt.Text(f"{val}:Q", format=fmt),
    )
    h = height or (60 + 30 * len(df) if horizontal else 320)
    st.altair_chart(
        (bars + text).properties(title=title, height=h).configure_axis(labelLimit=260),
        width="stretch",
    )


def has(*tables: str) -> bool:
    return all(table_exists(t) for t in tables)


PAGES = [
    "1 · The problem",
    "2 · The case: Meridian",
    "3 · The approach",
    "4 · Bronze: catalog, not meaning",
    "5 · Discovery: events vs crawler",
    "6 · Silver: the gate",
    "7 · Gold: rule-based flags",
    "8 · Embeddings: meaning as numbers",
    "9 · Taxonomy: classify",
    "10 · Search: raw vs filtered",
    "11 · Extraction: regex vs extract()",
    "12 · Evals: is the AI right?",
    "13 · Cost & lineage",
    "14 · Wrap-up",
    "A · SQL pack",
    "B · Glossary (labels & terms)",
]

st.sidebar.markdown("### Folio")
st.sidebar.caption("Medallion × context engineering")
st.sidebar.markdown(
    "**Act I** Problem (1–3)  \n**Act II** Ingest (4–6)  \n**Act III** Structure (7–9)  \n"
    "**Act IV** Use it (10–11)  \n**Act V** Trust (12–14)"
)
page = st.sidebar.radio("Talk pages (in order)", PAGES)
st.sidebar.caption("Lost on a word? Open **B · Glossary** — labels, credit terms, AI terms.")
st.sidebar.markdown("---")
_stats = cache_stats()
if WAREHOUSE == "bigquery":
    st.sidebar.caption(f"BigQuery · `{BQ_PROJECT}.{BQ_DATASET}`")
else:
    st.sidebar.caption("DuckDB · folio.duckdb")
st.sidebar.caption(
    f"Query cache · {_stats['files']} files" + (" · warmed" if _stats["warmed"] else " · cold")
)
if st.sidebar.button("Warm all queries"):
    with st.spinner("Fetching talk queries into local cache…"):
        _bar = st.sidebar.progress(0.0)

        def _prog(i, total, label):
            _bar.progress(min(i / max(total, 1), 1.0))

        result = warm_talk_cache(force=True, progress=_prog)
    st.sidebar.success(f"ok={len(result['ok'])} err={len(result['errors'])}")
    st.rerun()
if st.sidebar.button("Refresh data (clear cache)"):
    clear_disk_cache()
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

if not _stats["warmed"] and _stats["files"] < 5:
    with st.spinner("Preloading BigQuery results for the talk…"):
        warm_talk_cache(force=False)
    st.rerun()


def next_up() -> None:
    i = PAGES.index(page)
    if i + 1 < len(PAGES):
        st.markdown(f'<div class="nextup">Next → <b>{PAGES[i + 1]}</b></div>', unsafe_allow_html=True)


# ===========================================================================
# ACT I — THE PROBLEM
# ===========================================================================
if page == PAGES[0]:
    hero(
        "Credit risk lives in documents, not tables",
        "A bank analyst has to judge one borrower. The evidence is scattered across PDFs.",
    )
    st.markdown(
        '<div class="question"><b>The question every credit team asks:</b><br/>'
        "“Is this borrower heading toward a covenant breach — and which documents prove it?”</div>",
        unsafe_allow_html=True,
    )
    if has("bronze_document_catalog"):
        cat = load("corpus_counts").iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Files in the folder", int(cat["docs"]))
        c2.metric("Borrowers", int(cat["accounts"]))
        c3.metric("Document formats", int(cat["doc_types"]))

    st.markdown("### Why a normal warehouse cannot answer it")
    left, right = st.columns(2)
    with left:
        st.markdown(
            """
            **1 · The signal is scattered**
            A past-due invoice, a covenant limit in a loan agreement, a slowing-receivables
            remark on an earnings call. No single file says “risky”.

            **2 · The files are noisy**
            Most borrowers are healthy. Their boilerplate buries the one that matters.

            **3 · Some files are unusable**
            Blank scans, garbled OCR, a memo with a social-security number.
            """
        )
    with right:
        st.markdown(
            """
            **4 · AI is billed per token**
            Embedding everything — including junk and PII — costs money and pollutes search.

            **5 · Answers need proof**
            An answer without file, hash and quote is a demo, not something audit accepts.

            **The pattern in this talk**
            Bronze → Silver → Gold, then AI **only on what passed the gate**, with tests and a cost ledger.
            """
        )
    teach(
        "<b>Today’s agenda</b> — we follow one file folder through five acts:<br/>"
        "I Problem · II Ingest (Bronze, Silver) · III Structure (Gold, embeddings, taxonomy) · "
        "IV Use it (search, extraction) · V Trust (evals, cost, lineage)."
    )
    next_up()

# ===========================================================================
elif page == PAGES[1]:
    hero(
        "The case: Meridian Industrial Corp",
        "One stressed borrower (ACC-8847) hidden inside a folder of 12 borrowers.",
    )
    if not has("bronze_document_catalog"):
        st.warning("Run dbt build on BigQuery first.")
        st.stop()

    acc = load("corpus_by_account").copy()
    acc["who"] = acc["account_id"].map(lambda a: "Meridian (the case)" if a == MERIDIAN else "Other borrowers")
    st.subheader("How many files does each borrower have?")
    bar(
        acc,
        "account_name",
        "docs",
        title="Files per borrower (Bronze catalog)",
        cat_title="Borrower",
        val_title="Number of files",
        color="who",
        colors={"Meridian (the case)": RED, "Other borrowers": GREY},
    )
    guide(
        "Y = borrower name · X = how many files we hold for them.",
        "Red bar is Meridian; grey bars are healthy borrowers with mostly routine paperwork.",
        "Meridian has the most files, but 11 other borrowers have 7–9 each — a keyword search over everything "
        "returns plenty of other people’s paperwork.",
    )

    st.subheader("Meridian’s case file — what the analyst has to read")
    case = load("meridian_case").rename(
        columns={
            "doc_id": "File",
            "doc_type": "Type",
            "title": "Title",
            "effective_date": "Date",
            "silver_status": "Usable? (Silver status)",
        }
    )
    st.dataframe(case, width="stretch", hide_index=True)
    teach(
        f"<b>Read the table</b> — {len(case)} files, 6 formats (invoice, credit memo, analyst note, credit facility, "
        "earnings call, SEC filing). One of them is a memo containing an SSN, so it is already marked "
        "<code>quarantine_pii_review</code> — we will come back to that on the Silver page.<br/><br/>"
        "<b>What we want at the end:</b> a short list of the documents that show the stress, "
        "each with a quote, a file hash and a confidence we can test."
    )
    next_up()

# ===========================================================================
elif page == PAGES[2]:
    hero(
        "The approach: medallion + context engineering",
        "Classic data layers, applied to PDFs — AI is the last step, not the first.",
    )
    cols = st.columns(4)
    cols[0].markdown(card("🥉 Bronze", "Catalog the file: where is it, what hash, what type. <i>No interpretation.</i>"), unsafe_allow_html=True)
    cols[1].markdown(card("🥈 Silver", "Parse, score quality, label sensitivity. <i>Bad files are quarantined.</i>"), unsafe_allow_html=True)
    cols[2].markdown(card("🥇 Gold", "Facts you can explain: SQL flags and simple tiers per document and borrower."), unsafe_allow_html=True)
    cols[3].markdown(card("🧠 Context", "Chunk → embed → classify → search → extract, <i>behind cost gates</i>."), unsafe_allow_html=True)

    teach(
        "<b>Two kinds of “Gold” (we compare them on pages 7 and 11)</b><br/>"
        "• <b>Rule-based</b> — regular expressions in SQL. Free, instant, easy to explain, but literal: "
        "it matches the word, not the meaning.<br/>"
        "• <b>AI-based</b> — embeddings, classify, extract. Understands meaning, costs tokens, "
        "so it must be gated and measured.<br/>"
        "The talk is not “replace SQL with RAG”. It is: govern both."
    )
    st.markdown(
        """
        | Capability (package `dbt_context_engineering`) | Folio model | Plain meaning |
        |---|---|---|
        | `chunk` / `embed` | `documents_embed` | Cut text into passages and turn each into numbers that capture meaning |
        | `classify` | `documents_classify` | Give each passage one label from a closed list |
        | `vector_search` | `search` | Find passages closest in meaning to a question, with citations |
        | `extract` | `documents_extract_flat` | Pull typed fields (signal, leverage, amount) **plus a quote** |
        | `eval` / `grounded` | `gov_classify_eval` | Score the AI against known answers; fail if a quote is invented |
        | `guard_batch` / `log_ai_run` | `gov_ai_spend` | Stop oversized jobs; record tokens and cost |
        """
    )

    st.subheader("How Folio maps to the unstructured-medallion article")
    st.markdown(
        """
        | Article layer | What the article asks for | Folio model(s) |
        |---|---|---|
        | 🥉 **Bronze** | Catalog, zero-copy by default, immutable | `bronze_document_versions` (append-only log) → `bronze_document_catalog` (current-version view) |
        | 🥈 **Silver** | Parse, quality gate, PII redaction, dedup | `silver_document_bodies` (status CASE + `body_sanitized` + `silver_version_id`) → `silver_ready_documents` |
        | 🥇 **Gold · context store** | Chunks + embeddings, reusable | `documents_hashed`, `documents_embed` (public, incremental) |
        | 🥇 **Gold · structured** | Tables you can join | `gold_document_facts`, `gold_document_periods` (regex → AI), `documents_extract_flat` |
        | 🥇 **Gold · serving** | Use-case products | `documents_classify`, `search`, `knowledge_base` |
        | 🥇 **Gold · governance** | Lineage, spend, health | `gov_document_lineage`, `gov_ai_spend`, `gov_medallion_health` |
        """
    )
    teach(
        "<b>Honest gaps vs the article</b> — not built in this demo: ACL propagation from the source system, "
        "a human steward queue for quarantined files, and near-duplicate detection (MinHash). We only "
        "dedupe <i>exact</i> copies (same sha256)."
    )
    next_up()

# ===========================================================================
# ACT II — INGEST
# ===========================================================================
elif page == PAGES[4]:
    hero(
        "Discovery: how do files get into the catalog?",
        "Bronze is a catalog — someone has to fill it. Push (events) or pull (crawler); Folio seeds it for the demo.",
    )
    teach(
        "<b>Read the diagram left → right</b><br/>"
        "• <b>Event-driven</b> — a file upload fires an event → queue → worker → catalog. Near real-time, "
        "you pay only when files change.<br/>"
        "• <b>Crawler</b> — a schedule lists the whole bucket, compares hashes, sends only the delta. "
        "Finds everything, but is chatty and late."
    )
    show_asset("event-vs-crawler.jpeg", "S3 event-driven (push) vs crawler (scheduled pull)")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Event-driven (push)")
        st.markdown(
            "- Instant catalog + parse kickoff\n- Idle cost ≈ $0\n"
            "- Gap: files that never emit events (“dark data”)"
        )
    with right:
        st.markdown("#### Crawler (pull)")
        st.markdown(
            "- Complete inventory after each pass\n- Cost: API calls + delay until next run\n"
            "- Needs state to know what is new"
        )
    st.success(
        "**Recommended:** crawl once for the baseline → events day to day → re-crawl periodically to catch misses."
    )
    with st.expander("Article framing — discovery landscape"):
        show_asset("discovery-ingestion.png", "Data discovery & ingestion — Jojo Joseph, Part 3")
    next_up()

# ===========================================================================
elif page == PAGES[3]:
    hero(
        "Bronze: a catalog, not meaning",
        "Bronze answers “what file is this and can I prove it didn’t change?” — nothing more.",
    )
    show_asset("medallion-unstructured.png", "Medallion for unstructured data — Jojo Joseph, Beyond Tables")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Metadata-only (zero-copy)")
        st.markdown(
            "- Store URI + type + `sha256`; leave the file where it is\n- Less storage, smaller attack surface\n"
            "- Trade-off: re-parsing hits the source; links can rot"
        )
    with right:
        st.markdown("#### Physical copy (snapshot)")
        st.markdown(
            "- Keep a copy in a landing zone\n- Audit trail if the source overwrites the file\n"
            "- Trade-off: duplicate storage and security perimeter"
        )
    st.info(
        "**Folio demo:** physical-copy PDFs in git, loaded with `dbt seed`. "
        "**Production lean:** metadata-only Bronze with selective snapshots for regulated records."
    )
    if has("bronze_document_catalog"):
        st.subheader("Live Bronze catalog (first rows)")
        st.dataframe(load("bronze_catalog_sample").head(12), width="stretch", hide_index=True)
        teach(
            "<b>Columns to point at</b>: <code>uri</code> = where the file lives · "
            "<code>content_sha256</code> = fingerprint (same file ⇒ same hash; this is our audit anchor) · "
            "<code>bronze_layer</code> = physical_copy vs metadata_only."
        )

    if has("bronze_document_versions"):
        st.subheader("Append-only: Bronze never overwrites a row")
        vc = load("bronze_version_counts").iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Version rows (immutable log)", int(vc["version_rows"]))
        c2.metric("Distinct documents", int(vc["docs"]))
        c3.metric("Arrived in batch 2", int(vc["batch2_rows"]))
        teach(
            "<b>Two tables, one rule.</b> <code>bronze_document_versions</code> is an append-only log: a row is "
            "identified by <code>(doc_id, content_sha256)</code>, inserted once, never updated or deleted, and "
            "<code>--full-refresh</code> is blocked unless <code>allow_bronze_rebuild=true</code>. "
            "<code>bronze_document_catalog</code> is just a <i>view</i> of the latest version per document. "
            "A singular test fails the build if any version is duplicated or missing."
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**Same document, file changed → new version (v1 is kept)**")
            st.dataframe(load("bronze_revised_docs"), width="stretch", hide_index=True)
            st.dataframe(
                load("bronze_inv4401_text").rename(columns={"status_line": "Status line in the PDF", "total_due": "Total due"}),
                width="stretch",
                hide_index=True,
            )
        with right:
            st.markdown("**Different document, identical bytes → same hash**")
            st.dataframe(load("bronze_same_hash"), width="stretch", hide_index=True)
            st.caption("The email re-send keeps its own Bronze row (provenance!) but Silver will quarantine it as a duplicate.")
        guide(
            "Each row is one registered version of one file. `sha256_prefix` is its fingerprint.",
            "INV-4401 has two rows with different hashes: the vendor re-issued the invoice (late fee added). "
            "MER-X02 and MER-X02-DUP share one hash: someone e-mailed the same PDF again.",
            "Bronze records what arrived and when — it never decides which one matters. That is Silver’s job.",
        )
    next_up()

# ===========================================================================
elif page == PAGES[5]:
    hero(
        "Silver: the gate before any AI spend",
        "Silver parses each file and decides whether it is allowed downstream.",
    )
    if not has("silver_document_bodies"):
        st.warning("Missing silver_document_bodies.")
        st.stop()

    teach(
        "<b>The “silver gate” is a column, not a separate table.</b> "
        "<code>silver_status</code> in <code>silver_document_bodies</code> is set by a CASE — first rule that matches wins:<br/>"
        "1 · parse failed → <code>quarantine_parse_failed</code><br/>"
        "2 · quality score &lt; 0.4 → <code>quarantine_low_quality</code><br/>"
        "3 · sensitivity = restricted_pii → <code>quarantine_pii_review</code><br/>"
        "4 · same <code>content_sha256</code> already seen earlier → <code>quarantine_duplicate</code><br/>"
        "5 · otherwise → <code>silver_ready</code><br/>"
        "Everything downstream reads the view <code>silver_ready_documents</code>, which keeps only #5. "
        "Silver reads only the <i>current</i> Bronze version of each document."
    )

    bodies = load("silver_bodies").copy()
    STATUS_ORDER = [
        "silver_ready",
        "quarantine_parse_failed",
        "quarantine_low_quality",
        "quarantine_pii_review",
        "quarantine_duplicate",
    ]
    STATUS_COLORS = [GREEN, RED, AMBER, "#7d3c98", "#4b6a88"]
    bodies["silver_status"] = pd.Categorical(bodies["silver_status"], STATUS_ORDER, ordered=True)
    bodies = bodies.sort_values(["silver_status", "doc_id"]).reset_index(drop=True)
    bodies["silver_status"] = bodies["silver_status"].astype(str)
    bodies["col"] = bodies.index % 10
    bodies["row"] = bodies.index // 10
    ready = int((bodies["silver_status"] == "silver_ready").sum())
    quar = len(bodies) - ready

    c1, c2, c3 = st.columns(3)
    c1.metric("Files entering Silver", len(bodies))
    c2.metric("Passed to Gold + AI", ready)
    c3.metric("Quarantined (never embedded)", quar)

    st.subheader("Every file, one square")
    waffle = (
        alt.Chart(bodies)
        .mark_square(size=620)
        .encode(
            x=alt.X("col:O", axis=None),
            y=alt.Y("row:O", axis=None),
            color=alt.Color(
                "silver_status:N",
                scale=alt.Scale(domain=STATUS_ORDER, range=STATUS_COLORS),
                legend=alt.Legend(title="silver_status", orient="right"),
            ),
            tooltip=["doc_id", "account_id", "doc_type", "silver_status", "quality_score"],
        )
        .properties(title=f"{len(bodies)} files after the Silver gate (hover for the file)", height=330, width=420)
    )
    st.altair_chart(waffle, width="content")
    guide(
        "No axes — each square is one file (hover to see which). Squares are sorted by status, green first.",
        "Green = allowed downstream. Every other colour = quarantined, one colour per rule that stopped it.",
        f"{quar} of {len(bodies)} files are blocked. They never reach Gold, are never embedded and never cost tokens. "
        "The gate is rare on purpose — most files are fine; the point is the ones that are not.",
    )

    st.subheader("Quality score vs the 0.4 rule")
    hist = (
        alt.Chart(bodies)
        .mark_bar()
        .encode(
            x=alt.X("quality_score:Q", bin=alt.Bin(step=0.1), title="Parse quality score (0 = garbage, 1 = perfect)"),
            y=alt.Y("count():Q", title="Number of files"),
            color=alt.Color(
                "silver_status:N",
                scale=alt.Scale(domain=STATUS_ORDER, range=STATUS_COLORS),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=["silver_status", "count()"],
        )
    )
    rule = alt.Chart(pd.DataFrame({"x": [0.4]})).mark_rule(color="#1a2332", strokeDash=[6, 4], size=2).encode(x="x:Q")
    label = (
        alt.Chart(pd.DataFrame({"x": [0.4], "t": ["rule 2: quality < 0.4 is quarantined"]}))
        .mark_text(align="left", dx=6, dy=-4, baseline="bottom", color="#1a2332")
        .encode(x="x:Q", y=alt.value(12), text="t:N")
    )
    st.altair_chart(
        (hist + rule + label).properties(title="Files by quality score, coloured by gate verdict", height=300),
        width="stretch",
    )
    guide(
        "X = parse quality score in bins of 0.1 · Y = number of files · colour = gate verdict.",
        "Anything left of the dashed line fails rule 2. A parse-failed file has no usable text, whatever its score. "
        "The purple file sits on the right of the line — good quality, but blocked by rule 3 (it contains an SSN).",
        "The gate is not only a quality filter: sensitivity is a separate reason to stop a file.",
    )

    st.subheader("The quarantined files — and why")
    qdf = load("silver_quarantined").copy()
    reason = {
        "quarantine_parse_failed": "Could not extract text (blank / illegible scan)",
        "quarantine_low_quality": "Text extracted but garbled (OCR quality below 0.4)",
        "quarantine_pii_review": "Contains personal data (SSN) — needs human review",
        "quarantine_duplicate": "Byte-identical copy of a file already accepted (same sha256)",
    }
    qdf.insert(1, "why", qdf["silver_status"].map(reason))
    st.dataframe(qdf, width="stretch", hide_index=True)

    st.markdown("#### Why not skip Silver? (the anti-pattern)")
    c1, c2 = st.columns(2)
    c1.markdown(
        card("❌ Bronze → Vector", "Embeds the blank scan, the garbled fax <i>and</i> the SSN memo. "
             "The index now holds data nobody approved, and the AI will cite it."),
        unsafe_allow_html=True,
    )
    c2.markdown(
        card("✅ Bronze → Silver → Vector", "Only gate-passed text is chunked and embedded. "
             "Vectors without Silver are an <b>ungoverned second copy</b> of your data."),
        unsafe_allow_html=True,
    )
    next_up()

# ===========================================================================
# ACT III — STRUCTURE
# ===========================================================================
elif page == PAGES[6]:
    hero(
        "Gold: rule-based risk flags",
        "Plain SQL looks for words in each Silver document. Fast and explainable — but literal.",
    )
    if not has("gold_account_risk_rollup", "gold_document_facts"):
        st.error("Missing Gold tables — run dbt build on BigQuery.")
        st.stop()

    teach(
        "<b>This is not a credit score.</b> For every <code>silver_ready</code> document SQL checks three word lists:<br/>"
        "• <code>flag_past_due</code> — “past due”, “overdue”, “credit hold”<br/>"
        "• <code>flag_covenant_language</code> — “covenant”, “leverage ratio”, “event of default”<br/>"
        "• <code>flag_liquidity_language</code> — “working capital”, “DSO”, “liquidity”<br/><br/>"
        "Tier per document: <span class='tier-high'>high</span> = covenant <b>and</b> liquidity words · "
        "<span class='tier-med'>medium</span> = any one flag · <span class='tier-low'>low</span> = none."
    )

    tiers = load("gold_tier_counts").set_index("risk_signal_tier")["docs"]
    t1, t2, t3 = st.columns(3)
    t1.metric("high tier", int(tiers.get("high", 0)), help="covenant AND liquidity words in the same document")
    t2.metric("medium tier", int(tiers.get("medium", 0)), help="exactly one kind of flag")
    t3.metric("low tier", int(tiers.get("low", 0)), help="no flag")

    st.subheader("Which borrowers have flagged documents?")
    by_acct = load("gold_tier_by_account").copy()
    by_acct["tier_rank"] = by_acct["risk_signal_tier"].map({"high": 0, "medium": 1, "low": 2})
    names = (
        by_acct.groupby("account_name")["docs"].sum().sort_values(ascending=False).index.tolist()
    )
    chart = (
        alt.Chart(by_acct)
        .mark_bar()
        .encode(
            y=alt.Y("account_name:N", sort=names, title="Borrower"),
            x=alt.X("docs:Q", title="Number of documents (each document counted once)"),
            color=alt.Color(
                "risk_signal_tier:N",
                scale=alt.Scale(domain=["high", "medium", "low"], range=[RED, AMBER, "#c9d1d9"]),
                legend=alt.Legend(title="Tier", orient="bottom"),
            ),
            order=alt.Order("tier_rank:Q"),
            tooltip=["account_name", "risk_signal_tier", "docs"],
        )
        .properties(title="Documents per borrower, split by regex tier", height=420)
    )
    st.altair_chart(chart, width="stretch")
    guide(
        "Y = borrower (all 12) · X = number of documents · colour = tier (red high, amber medium, light grey low).",
        "Each document is counted once, in its tier. The coloured part of a bar is what the rules consider risky.",
        "Meridian is mostly red/amber. Ten borrowers are all grey. Two others show one amber document each "
        "(Summit Rail, BrightPeak) — remember them: page 11 checks whether the rules were right.",
    )

    st.subheader("Look inside one borrower: which flag did each Meridian document trip?")
    facts = load("gold_meridian_facts").copy()
    flag_cols = {
        "flag_past_due": "past due",
        "flag_covenant_language": "covenant",
        "flag_liquidity_language": "liquidity",
    }
    heat = facts.melt(
        id_vars=["doc_id", "risk_signal_tier"],
        value_vars=list(flag_cols),
        var_name="flag",
        value_name="hit",
    )
    heat["flag"] = heat["flag"].map(flag_cols)
    heat["hit"] = heat["hit"].map(lambda v: "flag on" if bool(v) else "no match")
    tier_rank = {"high": 0, "medium": 1, "low": 2}
    doc_order = sorted(
        facts["doc_id"].tolist(),
        key=lambda d: (tier_rank[facts.loc[facts["doc_id"] == d, "risk_signal_tier"].iloc[0]], d),
    )
    heat["doc_label"] = heat["doc_id"] + "  [" + heat["risk_signal_tier"] + "]"
    label_order = [
        d + "  [" + facts.loc[facts["doc_id"] == d, "risk_signal_tier"].iloc[0] + "]" for d in doc_order
    ]
    hm = (
        alt.Chart(heat)
        .mark_rect(stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("flag:N", title="Word list matched", sort=["past due", "covenant", "liquidity"], axis=alt.Axis(labelAngle=0)),
            y=alt.Y("doc_label:N", title="Meridian document  [tier]", sort=label_order),
            color=alt.Color(
                "hit:N",
                scale=alt.Scale(domain=["flag on", "no match"], range=[RED, "#eef1f4"]),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=["doc_id", "flag", "hit", "risk_signal_tier"],
        )
        .properties(title="Meridian: documents × flags", height=30 * len(facts) + 40)
    )
    st.altair_chart(hm, width="stretch")
    guide(
        "Y = one row per Meridian document, with its tier in brackets · X = the three word lists.",
        "A red cell means that word list matched somewhere in the document. "
        "Two red cells in covenant + liquidity = high; one red cell = medium; none = low.",
        "This is the whole “risk” logic — three yes/no questions. No model, no score. "
        "Easy to explain and to audit, but it only sees words.",
    )

    with st.expander("Same data as a table (with leverage mentions)"):
        st.dataframe(
            facts.rename(
                columns={
                    "flag_past_due": "past_due",
                    "flag_covenant_language": "covenant",
                    "flag_liquidity_language": "liquidity",
                    "leverage_ratio_mention": "leverage_x",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    next_up()

# ===========================================================================
elif page == PAGES[7]:
    hero(
        "Embeddings: meaning as numbers",
        "An embedding turns a passage into a list of ~768 numbers. Similar meaning ⇒ nearby numbers.",
    )
    if not has("documents_embed"):
        st.warning("Build the AI layer: `dbt build --select documents_embed+ --vars '{\"embeddings_enabled\": true}'`")
        st.stop()

    teach(
        "<b>Plain-language model</b>: imagine a map where every passage is a dot. Invoices about overdue payments "
        "sit in one neighbourhood, covenant memos in another. “Search” = find the dots nearest your question.<br/>"
        "<b>In the table</b>: <code>chunk_text</code> (the passage) · <code>embedding</code> (the numbers) · "
        "<code>content_hash</code> (re-embed only if the text changes) · <code>embedding_fn_fingerprint</code> "
        "(model change ⇒ rebuild)."
    )
    s = load("embed_stats").iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Chunks embedded", int(s["chunks"]))
    c2.metric("Borrowers covered", int(s["accounts"]))
    c3.metric("Numbers per chunk", int(s["dims"] or 0))
    c4.metric("Model", str(s["model_version"]))

    st.subheader("Proof it works: nearest neighbours of one chunk")
    nn = load("embed_neighbours").copy()
    anchor = nn.iloc[0]
    st.caption(f"Anchor chunk: **{anchor['chunk_id']}** — {anchor['preview']}…")
    nn["is_anchor"] = nn["chunk_id"].map(lambda c: "anchor" if c == anchor["chunk_id"] else "neighbour")
    bar(
        nn,
        "chunk_id",
        "similarity",
        title="Cosine similarity to the anchor (top 10)",
        cat_title="Chunk",
        val_title="Similarity (1.0 = identical meaning)",
        color="doc_type",
        fmt=".2f",
    )
    guide(
        "Y = chunk id · X = cosine similarity to the anchor chunk (computed in SQL with ML.DISTANCE) · colour = document type.",
        "Longer bar = closer in meaning. The first bar is the anchor itself (1.0).",
        "The anchor is a past-due invoice and the nearest chunks are other invoices — without sharing a keyword list. "
        "Then the covenant memos appear, further away. That is “meaning”, measured.",
    )
    with st.expander("Sample rows from the embeddings mart"):
        st.dataframe(load("embed_meridian_sample"), width="stretch", hide_index=True)
    with st.expander("SQL — nearest neighbours"):
        st.code(talk_queries()["embed_neighbours"].strip() + ";", language="sql")
    next_up()

# ===========================================================================
elif page == PAGES[8]:
    hero(
        "Taxonomy: classify every chunk",
        "A closed list of labels lets us filter search results. The label set is a product decision.",
    )
    if not has("gov_classification_breakdown"):
        st.warning("Missing gov_classification_breakdown.")
        st.stop()

    teach(
        "<b>Five labels</b> (prompt <code>folio_content_type.v1</code>):<br/>"
        "<code>covenant_or_credit_risk</code> · <code>liquidity_or_working_capital</code> · "
        "<code>supplier_collections</code> · <code>public_disclosure</code> · <code>routine_transaction</code> "
        "(everything boring).<br/>The model picks exactly one per chunk."
    )
    with st.expander("📖 What does each label mean? (plain-language definitions)", expanded=True):
        st.markdown(as_markdown(LABELS))
        st.caption("Example phrases are illustrative wording, not quotes from the corpus. Full glossary: page B.")
    tax = load("taxonomy").copy()
    tax["kind"] = tax["classification"].map(
        lambda c: "routine / disclosure" if c in ("routine_transaction", "public_disclosure") else "risk label"
    )
    bar(
        tax,
        "classification",
        "chunk_count",
        title="Chunks per label",
        cat_title="Label",
        val_title="Number of chunks",
        color="kind",
        colors={"risk label": RED, "routine / disclosure": GREY},
    )
    guide(
        "Y = label assigned by classify() · X = number of text chunks.",
        "Red = the three labels an analyst cares about; grey = routine paperwork and public filings.",
        "The risk labels are a small slice, and come from one borrower. A filter on those labels removes "
        "most of the noise before search — that is the precision gain on the next page.",
    )
    st.dataframe(
        tax.rename(columns={"chunk_count": "chunks", "accounts": "borrowers", "documents": "docs"}),
        width="stretch",
        hide_index=True,
    )
    st.subheader("Example chunk per label")
    st.dataframe(load("classify_samples"), width="stretch", hide_index=True)
    next_up()

# ===========================================================================
# ACT IV — USE IT
# ===========================================================================
elif page == PAGES[9]:
    hero(
        "Search: raw similarity vs similarity + label filter",
        "Same question, same vectors. The only difference is a WHERE clause on the classify() label.",
    )
    if not has("search"):
        st.warning("Missing search model.")
        st.stop()

    st.markdown(
        '<div class="question">Question asked: <b>“Which borrower is at risk of default?”</b></div>',
        unsafe_allow_html=True,
    )
    cmp = load("search_compare")
    long = cmp.melt(
        id_vars=["demo"],
        value_vars=["meridian_hits", "other_borrower_hits"],
        var_name="who",
        value_name="n_results",
    )
    long["who"] = long["who"].map({"meridian_hits": "Meridian (relevant)", "other_borrower_hits": "Other borrowers (noise)"})
    long["demo"] = long["demo"].map(
        {"raw_cosine_only": "A · raw cosine only", "cosine_plus_label_filter": "B · cosine + label filter"}
    )
    chart = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("demo:N", title="Search variant", sort=["A · raw cosine only", "B · cosine + label filter"]),
            y=alt.Y("n_results:Q", title="Results out of top 10"),
            color=alt.Color(
                "who:N",
                scale=alt.Scale(domain=["Meridian (relevant)", "Other borrowers (noise)"], range=[GREEN, RED]),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=["demo", "who", "n_results"],
        )
        .properties(title="Who shows up in the top 10?", height=320)
    )
    st.altair_chart(chart, width="stretch")
    guide(
        "X = search variant · Y = how many of the top-10 results belong to each group · colour = Meridian vs other borrowers.",
        "A is plain vector similarity. B adds `classification in (covenant_or_credit_risk, liquidity_or_working_capital)`.",
        "In A, about half the top 10 are other borrowers’ routine credit-facility boilerplate that just sounds similar. "
        "In B every result is a Meridian risk document. Same model, same embeddings — better precision.",
    )

    det = load("search_detail")
    left, right = st.columns(2)
    for col, demo, label in (
        (left, "raw_cosine_only", "A · raw cosine only"),
        (right, "cosine_plus_label_filter", "B · cosine + label filter"),
    ):
        with col:
            st.markdown(f"#### {label}")
            d = det[det["demo"] == demo][["source_id", "account_key", "classification", "score", "snippet"]]
            st.dataframe(d, width="stretch", hide_index=True, height=420)
    st.caption("Look at the `account_key` column: anything other than ACC-8847 is noise for this question.")
    next_up()

# ===========================================================================
elif page == PAGES[10]:
    hero(
        "Extraction: rules vs extract()",
        "Same documents, two methods. Where do they disagree — and who is right?",
    )
    if not has("documents_extract_flat", "gold_document_facts"):
        st.warning("Missing documents_extract_flat — build the AI path.")
        st.stop()

    teach(
        "<b>What extract() does</b> — the model reads a document and returns a typed record: "
        "<code>primary_signal</code>, <code>leverage_mention</code>, <code>usd_amount_mention</code> and "
        "<code>evidence</code> (a quote). The <code>grounded</code> test fails the build if that quote is not "
        "literally in the source.<br/>"
        "<b>Cost gate</b>: we extract only Meridian plus anything the regex flagged, not every ready document."
    )
    cmp = load("regex_vs_extract").copy()
    counts = cmp.groupby("verdict", as_index=False).size().rename(columns={"size": "docs"})
    bar(
        counts,
        "verdict",
        "docs",
        title="Regex tier vs extract() signal — agreement",
        cat_title="Verdict",
        val_title="Number of documents",
        color="verdict",
        colors={"agree": GREEN, "regex false alarm": RED, "regex missed it": AMBER},
    )
    guide(
        f"Y = how the two methods compare on each of the {len(cmp)} documents · X = number of documents.",
        "Green = both say “risky” or both say “not”. Red = regex flagged it but the model reads it as not risky. "
        "Amber = regex saw nothing but the model found stress.",
        "Rules are right most of the time — but the misses are the ones that hurt. "
        "Keep rules for cheap triage; use the model where wording is subtle.",
    )

    st.subheader("The disagreements, with the model’s evidence quote")
    dis = cmp[cmp["verdict"] != "agree"][
        ["verdict", "doc_id", "title", "regex_tier", "extract_signal", "evidence"]
    ]
    st.dataframe(dis, width="stretch", hide_index=True)
    st.markdown(
        """
        - **CFA-2024-11** (Summit Rail) — regex sees “covenant” and calls it medium. It is a comfortable-headroom disclosure: no risk.
        - **EARN-Q2-BP** (BrightPeak) — regex sees “liquidity” in a routine call. The model reads *none*.
        - **INV-4412** (Meridian) — “cash timing pressure tied to delayed receivables”: no keyword, so regex scores low. The model catches it.
        """
    )
    with st.expander("Full extraction mart"):
        st.dataframe(load("extract_flat"), width="stretch", hide_index=True)

    if has("gold_document_periods"):
        st.subheader("Hybrid: regex first, AI only when regex fails")
        teach(
            "<b>Question:</b> which fiscal quarter does each document cover?<br/>"
            "<b>Step 1 · regex (free)</b> reads the canonical wording “… period: Q3 2025”.<br/>"
            "<b>Step 2 · AI <code>extract()</code> (billed)</b> runs <i>only</i> on documents that talk about a quarter in a shape "
            "the regex does not know (“the quarter ended September 30, 2025”, “third quarter of fiscal 2025”).<br/>"
            "<b>Step 3</b> · documents with no period at all are marked <code>not_found</code> — no AI call is wasted on them."
        )
        pm = load("period_methods").copy()
        order = ["regex", "ai", "not_found"]
        pm["fiscal_period_method"] = pm["fiscal_period_method"].astype(str)
        n_regex = int(pm.loc[pm["fiscal_period_method"] == "regex", "docs"].sum())
        n_ai = int(pm.loc[pm["fiscal_period_method"] == "ai", "docs"].sum())
        n_all = int(pm["docs"].sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Resolved by regex (free)", n_regex)
        c2.metric("Rescued by AI", n_ai)
        c3.metric("AI calls avoided", n_all - n_ai, help="documents that never reached the model")
        bar(
            pm,
            "fiscal_period_method",
            "docs",
            title="How each document’s fiscal period was resolved",
            cat_title="Method",
            val_title="Number of documents",
            color="fiscal_period_method",
            colors={"regex": GREEN, "ai": BLUE, "not_found": "#9aa5b1"},
            sort=order,
        )
        guide(
            "Y = method that produced the fiscal period · X = number of documents.",
            "Green = regex was enough. Blue = regex failed but the text had a quarter phrase, so the model filled it in. "
            "Grey = no period in the text at all (nothing to extract).",
            f"The model saw {n_ai} of {n_all} documents, not all of them — the regex is the cheap filter in front of the paid call.",
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**Regex hits** (canonical wording)")
            st.dataframe(load("period_regex_rows"), width="stretch", hide_index=True)
        with right:
            st.markdown("**AI rescues** — with the quote that proves it")
            st.dataframe(load("period_ai_rows"), width="stretch", hide_index=True)
        st.caption(
            "`documents_period_fallback` is incremental on (doc_id, silver_version_id, prompt+model version): "
            "a document is sent to the model once, and `grounded` fails the build if the quote is not in the text."
        )
    next_up()

# ===========================================================================
# ACT V — TRUST
# ===========================================================================
elif page == PAGES[11]:
    hero(
        "Evals: is the AI right?",
        "We keep a small answer key (golden set) and score the model against it — like a unit test.",
    )
    if not has("gov_classify_eval"):
        st.warning("gov_classify_eval not built yet.")
        st.stop()

    teach(
        "<b>How it works</b>: a seed (<code>eval_classify_golden</code>) lists 15 Meridian documents with the label a human "
        "expects. <code>classify()</code> labels their chunks; each document takes its majority label; "
        "<code>eval()</code> compares.<br/>"
        "<b>Words</b>: <b>precision</b> = when the model says label X, how often is it right? "
        "<b>recall</b> = of the documents that truly are X, how many did it find?"
    )
    metrics = load("classify_eval")
    overall = metrics[(metrics["metric"] == "accuracy") & (metrics["label"] == "__overall__")]
    c1, c2 = st.columns(2)
    if not overall.empty:
        c1.metric("Overall accuracy", f"{float(overall.iloc[0]['value']):.0%}")
    pairs = load("classify_eval_pairs")
    c2.metric("Documents wrong", int((~pairs["is_correct"].astype(bool)).sum()), help="out of " + str(len(pairs)))

    pr = metrics[metrics["metric"].isin(["precision", "recall"]) & (metrics["label"] != "__overall__")].copy()
    pr["value"] = pr["value"].astype(float)
    pr["shown"] = pr["value"].fillna(0.0)
    pr["text"] = pr["value"].map(lambda v: "n/a" if pd.isna(v) else f"{v:.2f}")
    base = alt.Chart(pr)
    enc_y = alt.Y("label:N", title="Label", sort=None)
    enc_x = alt.X("shown:Q", title="Score (0–1)", scale=alt.Scale(domain=[0, 1.12]))
    enc_off = alt.YOffset("metric:N")
    bars = base.mark_bar().encode(
        y=enc_y,
        x=enc_x,
        yOffset=enc_off,
        color=alt.Color(
            "metric:N",
            scale=alt.Scale(domain=["precision", "recall"], range=[BLUE, AMBER]),
            legend=alt.Legend(title=None, orient="bottom"),
        ),
        tooltip=["label", "metric", "text"],
    )
    labels = base.mark_text(align="left", dx=4, color="#1a2332").encode(
        y=enc_y, x=enc_x, yOffset=enc_off, text="text:N"
    )
    chart = (bars + labels).properties(title="Precision and recall per label", height=340)
    st.altair_chart(chart, width="stretch")
    guide(
        "Y = label · X = score from 0 to 1 · blue = precision, amber = recall.",
        "Full-length bars are perfect. “n/a” means undefined: precision for public_disclosure is n/a "
        "because the model never predicted that label for these documents, and its recall is 0.00.",
        "Accuracy is high but not perfect — and the misses are informative (next table).",
    )

    st.subheader("Where did it miss?")
    miss = pairs[~pairs["is_correct"].astype(bool)]
    st.dataframe(miss, width="stretch", hide_index=True)
    st.markdown(
        """
        - **10Q-Q3-MDA** — expected `public_disclosure`, predicted `covenant_or_credit_risk`. The filing text *is* about
          covenants. Either the label definition or the golden answer needs a product decision.
        - **EARN-Q3-2025** — expected `liquidity_or_working_capital`, predicted `covenant_or_credit_risk`. The call discusses both.

        **Takeaway:** the taxonomy is a product decision. Change the prompt or the label list, rerun `dbt build`,
        and these numbers move — you can regression-test it in CI.
        """
    )
    with st.expander("All golden pairs"):
        st.dataframe(pairs, width="stretch", hide_index=True)
    next_up()

# ===========================================================================
elif page == PAGES[12]:
    hero(
        "Cost & lineage: spend is gated, answers are traceable",
        "Every AI call is logged. Every file can be walked back to its Bronze hash.",
    )
    left, right = st.columns(2)
    with left:
        st.subheader("AI spend ledger")
        if has("gov_ai_spend"):
            spend = load("ai_spend")
            if spend.empty:
                st.info("No AI run events yet (build with ai_functions_enabled).")
            else:
                spend = spend.copy()
                spend["status"] = spend["completed"].map(lambda c: "completed" if c else "started, never finished")
                c1, c2, c3 = st.columns(3)
                c1.metric("AI runs", len(spend))
                c2.metric("Est. tokens", f"{float(spend['est_tokens'].fillna(0).sum()):,.0f}")
                c3.metric("Est. USD", f"${float(spend['est_cost_usd'].fillna(0).sum()):.4f}")
                by_fn = (
                    spend.groupby(["function_name", "status"], as_index=False)["est_tokens"].sum()
                )
                bar(
                    by_fn,
                    "function_name",
                    "est_tokens",
                    title="Estimated tokens per AI function",
                    cat_title="Function",
                    val_title="Estimated tokens",
                    color="status",
                    colors={"completed": GREEN, "started, never finished": RED},
                )
                guide(
                    "Y = AI function (embed / classify / extract) · X = estimated input tokens.",
                    "Green = the run logged both a start and a completion. Red = a job started and "
                    "never finished (an orphan) — here, a build that failed mid-way while we were developing. "
                    "The ledger caught it.",
                    "classify is the biggest line: the taxonomy prompt is re-sent with every chunk. "
                    "embed is the smallest because it is incremental on `content_hash` — unchanged text "
                    "is never re-billed. Both sit behind `guard_batch`.",
                )
                runs = load("billed_per_run").copy()
                runs = runs[runs["row_count"] > 0].reset_index(drop=True)
                runs["run"] = (runs.index + 1).astype(str).str.zfill(2) + " · " + runs["function_name"].astype(str)
                bar(
                    runs,
                    "run",
                    "row_count",
                    title="Rows sent to the model, run by run",
                    cat_title="Run (oldest first)",
                    val_title="Rows billed",
                    color="function_name",
                    colors={"embed": BLUE, "classify": AMBER, "extract": GREEN},
                    sort=runs["run"].tolist(),
                )
                guide(
                    "Y = each logged AI run, oldest first · X = rows that run sent to the model.",
                    "The first embed/classify runs process the whole corpus. The last ones process 2 rows: "
                    "only the chunks of the re-issued invoice INV-4401 changed (new Bronze version → new text hash).",
                    "Incremental AI models (embed, classify, period fallback) bill the delta, not the table. "
                    "Known gap: the 17-row credit `documents_extract` is still a plain table, so it re-bills on every build.",
                )
                st.dataframe(
                    spend[["function_name", "model_name", "row_count", "est_tokens", "est_cost_usd", "status"]],
                    width="stretch",
                    hide_index=True,
                )
        else:
            st.info("No gov_ai_spend yet.")
        st.caption("Gates: `max_batch_rows=5000`, `max_est_tokens=2,000,000` (vars.yml) — a runaway job fails before it bills.")

    with right:
        st.subheader("Lineage: Bronze → Gold")
        if has("gov_document_lineage"):
            ls = load("lineage_status_counts").copy()
            ls["lineage_status"] = ls["lineage_status"].astype(str)
            bar(
                ls,
                "lineage_status",
                "docs",
                title="Documents by lineage status",
                cat_title="Status",
                val_title="Number of documents",
                color="lineage_status",
                colors={"fully_promoted": GREEN, "quarantined": RED},
            )
            guide(
                "Y = how far a document got · X = number of documents.",
                "fully_promoted = made it through Silver and has chunks/flags. quarantined = stopped at the gate.",
                "Every row keeps `content_sha256` + `citation_url`, so any answer can name the exact file.",
            )
            lin = load("meridian_lineage")
            pick = st.selectbox("Drill into a Meridian document", lin["doc_id"].tolist())
            row = lin.loc[lin["doc_id"] == pick].iloc[0]
            st.code(
                f"doc_id:         {row['doc_id']}\n"
                f"content_sha256: {row['content_sha256']}\n"
                f"chunks:         {int(row['chunk_count']) if pd.notna(row['chunk_count']) else 0}\n"
                f"status:         {row['lineage_status']}",
                language="text",
            )
        else:
            st.info("No gov_document_lineage yet.")
    next_up()

# ===========================================================================
elif page == PAGES[13]:
    hero(
        "Wrap-up: what the folder became",
        "From raw files to a short, cited list — with every step gated and measured.",
    )
    if not has("gov_medallion_health"):
        st.warning("Missing gov_medallion_health.")
        st.stop()
    h = load("medallion_health").iloc[0]
    tiers = load("gold_tier_counts").set_index("risk_signal_tier")["docs"]
    flagged = int(tiers.get("high", 0) + tiers.get("medium", 0))
    funnel = pd.DataFrame(
        {
            "stage": ["1 Bronze (cataloged)", "2 Silver ready (passed gate)", "3 Gold facts", "4 Flagged by regex (medium/high)"],
            "docs": [int(h["bronze_docs"]), int(h["silver_ready"]), int(h["gold_fact_docs"]), flagged],
        }
    )
    bar(
        funnel,
        "stage",
        "docs",
        title="Document funnel",
        cat_title="Stage",
        val_title="Number of documents",
        sort=funnel["stage"].tolist(),
    )
    guide(
        "Y = pipeline stage · X = number of documents still in play.",
        "Each bar is what survives that step. The drop from 1 to 2 is the quarantine; from 3 to 4, the review queue.",
        "AI spend (embedding, classify, extract) runs on stage 2, not stage 1.",
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Quarantined", f"{100 * float(h['pct_quarantined'] or 0):.0f}%", help=f"{int(h['silver_quarantined'])} of {int(h['silver_docs'])} documents")
    c2.metric("AI tokens (est.)", f"{int(h['ai_total_est_tokens']):,}")
    c3.metric("AI cost (est.)", f"${float(h['ai_total_est_cost_usd']):.4f}")
    c4.metric("Orphaned AI runs", int(h["ai_orphaned_starts"] or 0))

    roll = load("gold_rollup")
    m = roll[roll["account_id"] == MERIDIAN]
    if not m.empty:
        m = m.iloc[0]
        st.markdown('<div class="question"><b>Answer to the opening question</b></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            **Meridian Industrial Corp** — {int(m['document_count'])} usable documents:
            **{int(m['past_due_docs'])}** with past-due language, **{int(m['covenant_docs'])}** with covenant language,
            **{int(m['liquidity_docs'])}** with liquidity language; leverage mentioned up to **{m['max_leverage_mentioned']}x**.
            The AI path adds quotes and removes the regex false alarms (page 11); search surfaces the risk documents
            without other borrowers’ noise (page 10); evals tell us how far to trust the labels (page 12).
            """
        )
    teach(
        "<b>Three sound bites</b><br/>"
        "1 · Vectors without Silver are an ungoverned second copy.<br/>"
        "2 · Rules are cheap and explainable; models understand meaning — use both and measure both.<br/>"
        "3 · Treat AI outputs like dbt models: tests, evals, cost ledger, lineage."
    )
    next_up()

# ===========================================================================
elif page == PAGES[15]:
    hero(
        "Glossary: labels and terms used in the talk",
        "Credit words, pipeline words and AI words — in plain language.",
    )
    needle = st.text_input("Filter (e.g. covenant, embedding, DSO)", "").strip().lower()

    def _filtered(rows):
        if not needle:
            return rows
        return [r for r in rows if needle in " ".join(r).lower()]

    sections = [
        ("Classification labels (the 5 `classify()` outputs)", LABELS),
        ("Credit & finance terms", CREDIT_TERMS),
        ("Pipeline & AI terms", PIPELINE_TERMS),
    ]
    shown = 0
    for title, rows in sections:
        rows = _filtered(rows)
        if not rows:
            continue
        shown += len(rows)
        st.subheader(title)
        st.markdown(as_markdown(rows))
    if not shown:
        st.info("No term matches that filter.")
    teach(
        "<b>Label cheat-sheet</b> — <code>covenant_or_credit_risk</code> = the lender is worried · "
        "<code>liquidity_or_working_capital</code> = cash is tight · <code>supplier_collections</code> = a vendor wants its money · "
        "<code>public_disclosure</code> = written for the market · <code>routine_transaction</code> = nothing to see."
    )

# ===========================================================================
else:
    hero(
        "SQL pack — click-through in BigQuery Studio",
        "Same queries as docs/presentation_queries.sql. Pick one, read it, run it.",
    )
    pack = [
        ("01 Bronze catalog  (page 4)", "pack_bronze"),
        ("02 Silver status mix  (page 6)", "pack_silver_status"),
        ("03 Gold tiers per borrower  (page 7)", "gold_tier_by_account"),
        ("04 Embeddings sample  (page 8)", "pack_embed"),
        ("05 Nearest neighbours  (page 8)", "embed_neighbours"),
        ("06 Search raw vs filtered  (page 10)", "pack_search"),
        ("07 Regex vs extract  (page 11)", "regex_vs_extract"),
        ("08 Classify eval  (page 12)", "classify_eval"),
        ("09 Bronze version history  (page 4)", "bronze_revised_docs"),
        ("10 Fiscal period: regex vs AI  (page 11)", "period_ai_rows"),
        ("11 Rows billed per run  (page 13)", "billed_per_run"),
    ]
    pick = st.selectbox("Query", [p[0] for p in pack])
    name = dict(pack)[pick]
    st.code(talk_queries()[name].strip() + ";", language="sql")
    if st.button("Run selected query"):
        try:
            st.dataframe(load(name), width="stretch", hide_index=True)
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
