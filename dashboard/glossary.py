"""Plain-language glossary for the Folio talk (labels, credit terms, pipeline/AI terms).

Label definitions mirror macros/prompts/folio_content_type.sql (v1) — keep them in sync.
"""

from __future__ import annotations

# (term, plain meaning, example / where you see it)
LABELS = [
    (
        "covenant_or_credit_risk",
        "Text about the lender's protections or worries: leverage covenants, amendments, headroom, "
        "events of default, credit-committee discussion, heightened monitoring of the borrower.",
        "“Leverage ratio 3.55x against a 3.50x maximum; waiver requested.”",
    ),
    (
        "liquidity_or_working_capital",
        "Text about cash and short-term funding: working capital, DSO/DPO, receivables aging, payables stretch, "
        "free cash flow, collections remediation.",
        "“DSO rose to 71 days; management is stretching supplier payments.”",
    ),
    (
        "supplier_collections",
        "A vendor chasing money: collection notices, past-due balances, credit holds, promise-to-pay language.",
        "“Second notice — invoice is 29 days overdue; account goes on credit hold.”",
    ),
    (
        "public_disclosure",
        "Language written for the market: SEC filings (10-Q MD&A), earnings-call commentary.",
        "“Management’s discussion of liquidity and capital resources …”",
    ),
    (
        "routine_transaction",
        "Everything boring: normal paid invoices, boilerplate facility language, healthy-borrower content. "
        "The default bucket — no risk signal.",
        "“Invoice paid on time; terms net-30.”",
    ),
]

CREDIT_TERMS = [
    (
        "Covenant",
        "A promise in a loan agreement (e.g. “keep debt below 3.5× earnings”). Breaking it can let the lender "
        "demand repayment or renegotiate.",
        "Why it matters: the analyst’s question is whether the borrower is heading toward a breach.",
    ),
    (
        "Leverage ratio",
        "Debt divided by earnings (usually EBITDA). Higher = more indebted. The `x` in 3.75x means 3.75 times.",
        "Gold extracts mentions like 3.55x with a regex.",
    ),
    (
        "Headroom",
        "How far a borrower is from breaking a covenant. “Headroom eroding” = getting closer.",
        "Summit Rail has comfortable headroom — a regex still flags the word “covenant”.",
    ),
    (
        "Event of default",
        "A formally defined failure (missed payment, broken covenant) that lets the lender act.",
        "",
    ),
    (
        "Waiver / amendment",
        "The lender agrees not to enforce a breach (waiver) or changes the terms (amendment).",
        "CFA-2025-03 is Meridian’s facility amendment.",
    ),
    (
        "Working capital",
        "Short-term assets minus short-term liabilities — the cash cushion for day-to-day operations.",
        "",
    ),
    (
        "DSO / DPO",
        "Days sales outstanding (how long customers take to pay) / days payables outstanding (how long the company "
        "takes to pay suppliers). Rising DSO + rising DPO = cash squeeze.",
        "",
    ),
    (
        "Past due / credit hold",
        "A bill not paid by its due date / a supplier stops shipping until it is paid.",
        "INV-4401 (AlloyForge → Meridian).",
    ),
    (
        "10-Q / MD&A",
        "A company’s quarterly SEC filing / its “Management’s Discussion & Analysis” section.",
        "Public disclosure — written for investors, not for credit decisions.",
    ),
    (
        "Fiscal period (Q3 2025)",
        "The quarter a document reports on. Folio resolves it hybrid: regex first, AI only when wording is unusual.",
        "Page 11.",
    ),
]

PIPELINE_TERMS = [
    ("Medallion (Bronze / Silver / Gold)", "Three data-quality layers: catalog the raw file → clean and gate it → build "
     "usable products. Each layer only reads the one before.", "Pages 3–7."),
    ("Bronze", "The catalog: where a file is, its hash, when it arrived. Append-only — new file version = new row.", "Page 4."),
    ("Silver gate", "A CASE column (`silver_status`) that blocks bad files: parse failed, low quality, PII, duplicate.", "Page 6."),
    ("Quarantine", "Files stopped by the gate. They never get chunked, embedded or billed.", ""),
    ("PII", "Personal data (e.g. an SSN). Redacted in `body_sanitized`; documents with restricted PII are held for review.", ""),
    ("sha256 / content hash", "A fingerprint of the file’s bytes. Same file ⇒ same hash; one changed byte ⇒ new hash.", "Used for lineage and dedup."),
    ("Chunk", "A short passage cut from a document (~120 tokens). The unit that is embedded and classified.", ""),
    ("Embedding", "A list of ~768 numbers that captures a passage’s meaning. Similar meaning ⇒ nearby numbers.", "Page 8."),
    ("Vector search", "Finding the chunks whose embeddings are closest to the embedding of your question.", "Page 10."),
    ("classify()", "AI function that gives each chunk exactly one label from a closed list.", "Page 9."),
    ("extract()", "AI function that reads a document and returns a typed record plus a verbatim quote.", "Page 11."),
    ("grounded (test)", "Fails the build if the model’s quote is not literally in the source text — catches invented evidence.", ""),
    ("Precision / recall", "Precision: when the model says X, how often is it right? Recall: of everything that truly is X, "
     "how much did it find?", "Page 12."),
    ("Golden set", "A small answer key written by humans, used to score the model like a unit test.", "Page 12."),
    ("Incremental model", "Only new or changed rows are processed on each run — unchanged text is never re-billed.", "Page 13."),
    ("guard_batch", "A cost circuit-breaker: the build fails before the AI call if the batch exceeds the row/token ceiling.", ""),
    ("Lineage", "Being able to walk any answer back to the exact Bronze file (hash + URL).", "Page 13."),
]


def as_markdown(rows, with_example: bool = True) -> str:
    head = "| Term | Plain meaning | Example / where |\n|---|---|---|\n" if with_example else "| Term | Meaning |\n|---|---|\n"
    out = [head.rstrip("\n")]
    for term, meaning, ex in rows:
        term_md = f"`{term}`" if term in {r[0] for r in LABELS} else f"**{term}**"
        out.append(f"| {term_md} | {meaning} | {ex} |" if with_example else f"| {term_md} | {meaning} |")
    return "\n".join(out)
