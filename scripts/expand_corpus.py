#!/usr/bin/env python3
"""Expand Folio demo corpus to ~100 PDFs + refresh Silver seeds.

Keeps the original Meridian story docs, adds noise accounts, and injects a few
quarantine / low-quality parses so Silver charts are not all `silver_ready`.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# Load generate_sample_pdfs as a module (hyphen-free path).
_gen_path = ROOT / "scripts" / "generate_sample_pdfs.py"
_spec = importlib.util.spec_from_file_location("generate_sample_pdfs", _gen_path)
gen = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gen)

ACCOUNTS = [
    ("ACC-8847", "Meridian Industrial Corp", "industrials"),
    ("ACC-1102", "BrightPeak Foods", "consumer_staples"),
    ("ACC-3301", "Summit Rail Partners", "transportation"),
    ("ACC-2201", "Cedar Ridge Chemicals", "materials"),
    ("ACC-4402", "Northwind Apparel", "consumer_discretionary"),
    ("ACC-5503", "Blue Harbor Utilities", "utilities"),
    ("ACC-6604", "Atlas Data Centers", "technology"),
    ("ACC-7705", "Prairie Ag Co-op", "consumer_staples"),
    ("ACC-8806", "Pacific Rim Logistics", "transportation"),
    ("ACC-9907", "Ironclad Construction", "industrials"),
    ("ACC-1010", "Lumen Health Systems", "health_care"),
    ("ACC-1111", "Skyline REITs", "real_estate"),
]

DOC_TYPES = [
    "invoice",
    "credit_facility",
    "credit_memo",
    "earnings_call",
    "sec_filing",
    "analyst_note",
    "supplier_email",
]

SOURCES = {
    "invoice": "ap_portal",
    "credit_facility": "treasury_vault",
    "credit_memo": "credit_risk",
    "earnings_call": "ir_transcripts",
    "sec_filing": "sec_edgar",
    "analyst_note": "research_desk",
    "supplier_email": "email_archive",
}


# ---------------------------------------------------------------------------
# Healthy-account filler ("noise"). Written to look like real, uneventful paperwork
# and to AVOID every Gold regex phrase (covenant / leverage ratio / event of default /
# past due / overdue / credit hold / working capital / DSO / liquidity), so the
# rollup chart stays readable and any hit on these accounts is a true surprise.
# ---------------------------------------------------------------------------
_NOISE_TEMPLATES: dict[str, list[str]] = {
    "invoice": [
        "Invoice for contracted services, payable on standard 30-day terms.",
        "Payment received in full on the due date. Account in good standing.",
    ],
    "credit_facility": [
        "Revolving credit facility, standard pricing grid, annual review completed.",
        "Borrower reported on time. No amendments requested. Commitment unchanged.",
    ],
    "credit_memo": [
        "Annual relationship review. Borrower profile unchanged since last cycle.",
        "Rating affirmed. Recommend renewing the existing limit on current terms.",
    ],
    "earnings_call": [
        "Management reviewed quarterly results and reaffirmed full-year guidance.",
        "Revenue grew modestly; margins in line with plan. No unusual items.",
    ],
    "sec_filing": [
        "Quarterly report: results of operations in line with prior periods.",
        "No material changes to risk factors since the last annual report.",
    ],
    "analyst_note": [
        "Initiating at neutral. Steady operator, fairly valued on current estimates.",
        "No change to estimates this quarter. Maintain rating.",
    ],
    "supplier_email": [
        "Confirming delivery schedule for next month. No issues to report.",
        "Thanks for the prompt payment. Purchase order attached for the next cycle.",
    ],
}


def _noise_body(account_id: str, account_name: str, doc_type: str, idx: int) -> list[str]:
    amt = 10_000 + (idx * 137) % 90_000
    lines = _NOISE_TEMPLATES[doc_type]
    return [
        f"Account: {account_name} ({account_id})",
        f"Reference: NOISE-{idx:03d}",
        "",
        "## Summary",
        lines[idx % len(lines)],
        f"Reference amount USD {amt:,}.00.",
        "",
        "## Notes",
        lines[(idx + 1) % len(lines)],
        "No watchlist items on this account.",
    ]


# ---------------------------------------------------------------------------
# Meridian follow-up documents. Eight DISTINCT items (different counterparties, numbers,
# wording) so retrieval results are not copies of one another.
# ---------------------------------------------------------------------------
_MERIDIAN_EXTRA: list[tuple[str, str, str, list[str]]] = [
    # (doc_type, title, effective_date, body)
    (
        "invoice", "Past-due notice - RiverBend Coatings", "2025-09-12",
        [
            "Vendor: RiverBend Coatings",
            "Bill-to: Meridian Industrial Corp (ACC-8847)",
            "Status: PAST DUE - 38 days. Credit hold warning issued.",
            "",
            "## Collections",
            "Open balance USD 28,400.00. Payment plan requested by Meridian AP.",
            "Vendor notes Meridian is stretching payables to protect working capital.",
        ],
    ),
    (
        "credit_memo", "Monitoring update - leverage certificate", "2025-09-26",
        [
            "Subject account: Meridian Industrial Corp (ACC-8847)",
            "",
            "## Update",
            "Interim leverage certificate printed 3.55x against the 3.75x amended covenant.",
            "Headroom is limited. Continue weekly cash reporting.",
            "Event of default risk rises if leverage exceeds 3.60x on the next certificate.",
        ],
    ),
    (
        "analyst_note", "Flash note - receivables slowing", "2025-10-08",
        [
            "Issuer: Meridian Industrial (ACC-8847)",
            "",
            "## Takeaway",
            "Days sales outstanding rose to 71 days from 58 a year ago.",
            "Cash conversion is thin and liquidity depends on the revolver into year-end.",
        ],
    ),
    (
        "invoice", "Overdue invoice - Delta Packaging", "2025-10-17",
        [
            "Vendor: Delta Packaging",
            "Bill-to: Meridian Industrial Corp (ACC-8847)",
            "Status: OVERDUE - 45 days past terms.",
            "",
            "## Collections",
            "Open balance USD 41,250.00. Two reminders sent, no payment date confirmed.",
            "Delta has moved Meridian to prepay-only pending a call with treasury.",
        ],
    ),
    (
        "credit_memo", "Waiver request - covenant cure period", "2025-10-29",
        [
            "Subject account: Meridian Industrial Corp (ACC-8847)",
            "",
            "## Request",
            "Borrower asks for a 60-day cure period if leverage prints above 3.60x.",
            "Credit committee to review the covenant waiver before the next test date.",
            "Sponsor equity support has not been confirmed in writing.",
        ],
    ),
    (
        "analyst_note", "Revolver usage climbing", "2025-11-06",
        [
            "Issuer: Meridian Industrial (ACC-8847)",
            "",
            "## Takeaway",
            "Revolver is 78% drawn, up from 52% in the spring.",
            "Remaining liquidity covers roughly two quarters of working capital needs.",
        ],
    ),
    (
        "invoice", "Partial payment - Kestrel Logistics", "2025-11-14",
        [
            "Vendor: Kestrel Logistics",
            "Bill-to: Meridian Industrial Corp (ACC-8847)",
            "Status: PARTIAL - credit hold on new shipments until balance clears.",
            "",
            "## Collections",
            "Open balance USD 19,780.00 after a USD 10,000.00 partial payment.",
        ],
    ),
    (
        "credit_memo", "Forecast - covenant step-down", "2025-11-25",
        [
            "Subject account: Meridian Industrial Corp (ACC-8847)",
            "",
            "## Forecast",
            "The covenant steps down to 3.50x in Q1. Current run-rate leverage is 3.58x.",
            "Without an amendment or deleveraging, a breach is likely at the Q1 test.",
        ],
    ),
]


def _meridian_extra(idx: int) -> tuple[str, str, str, list[str]]:
    return _MERIDIAN_EXTRA[idx % len(_MERIDIAN_EXTRA)]


def _quarantine_docs() -> list[dict]:
    """Docs that should fail Silver quality / parse gates (for the talk chart)."""
    return [
        {
            "doc_id": "SCAN-FAIL-01",
            "filename": "SCAN-FAIL-01_illegible_scan.pdf",
            "doc_type": "invoice",
            "account_id": "ACC-9907",
            "account_name": "Ironclad Construction",
            "effective_date": "2025-06-01",
            "source_system": "ap_portal",
            "title": "Illegible scan — Ironclad invoice (quarantine demo)",
            "body": ["x", ".", ""],  # too short → low quality
            "force_quality": 0.15,
            "force_parse": "failed",
        },
        {
            "doc_id": "OCR-LOW-02",
            "filename": "OCR-LOW-02_garbled_fax.pdf",
            "doc_type": "supplier_email",
            "account_id": "ACC-2201",
            "account_name": "Cedar Ridge Chemicals",
            "effective_date": "2025-07-14",
            "source_system": "email_archive",
            "title": "Garbled fax extract — Cedar Ridge (low quality)",
            "body": [
                "???? ##### %%%%",
                "unreadable scan fragment a b c",
                "no usable financial fields",
            ],
            "force_quality": 0.25,
            "force_parse": "ok",
        },
        {
            "doc_id": "DUP-EMPTY-03",
            "filename": "DUP-EMPTY-03_blank_pages.pdf",
            "doc_type": "sec_filing",
            "account_id": "ACC-5503",
            "account_name": "Blue Harbor Utilities",
            "effective_date": "2025-05-20",
            "source_system": "sec_edgar",
            "title": "Blank filing stub — Blue Harbor (quarantine)",
            "body": [" ", "  ", "   "],
            "force_quality": 0.1,
            "force_parse": "failed",
        },
        {
            "doc_id": "PII-RESTRICT-04",
            "filename": "PII-RESTRICT-04_ssn_leak_memo.pdf",
            "doc_type": "credit_memo",
            "account_id": "ACC-8847",
            "account_name": "Meridian Industrial Corp",
            "effective_date": "2025-10-02",
            "source_system": "credit_risk",
            "title": "Internal memo with SSN (sensitivity demo)",
            "body": [
                "Internal only — Meridian Industrial ACC-8847",
                "Borrower contact SSN 123-45-6789 must not be embedded.",
                "Covenant monitoring note; route to steward for redaction before Gold.",
            ],
            # quality ok so it is silver_ready but sensitivity = restricted_pii
        },
    ]


def build_documents(target: int = 100) -> list[dict]:
    docs = [dict(d) for d in gen.DOCUMENTS]  # original Meridian story + 3 healthy-account docs

    # Eight distinct Meridian follow-ups (the story keeps escalating through Q4).
    for i in range(len(_MERIDIAN_EXTRA)):
        doc_type, title, eff_date, body = _meridian_extra(i)
        doc_id = f"MER-X{i+1:02d}"
        docs.append(
            {
                "doc_id": doc_id,
                "filename": f"{doc_id}_{doc_type}.pdf",
                "doc_type": doc_type,
                "account_id": "ACC-8847",
                "account_name": "Meridian Industrial Corp",
                "effective_date": eff_date,
                "source_system": SOURCES[doc_type],
                "title": f"{title} ({doc_id})",
                "body": body,
            }
        )

    docs.extend(_quarantine_docs())

    # Filler for the OTHER 11 accounts only — Meridian's file is exactly the story docs.
    rng = random.Random(42)
    others = [a for a in ACCOUNTS if a[0] != "ACC-8847"]
    n = 1
    while len(docs) < target and n <= 500:
        aid, aname, _sector = others[n % len(others)]
        doc_type = DOC_TYPES[n % len(DOC_TYPES)]
        doc_id = f"NOISE-{n:03d}"
        docs.append(
            {
                "doc_id": doc_id,
                "filename": f"{doc_id}_{doc_type}.pdf",
                "doc_type": doc_type,
                "account_id": aid,
                "account_name": aname,
                "effective_date": f"2025-{(1 + n % 12):02d}-{(1 + n % 27):02d}",
                "source_system": SOURCES[doc_type],
                "title": f"{aname} {doc_type.replace('_', ' ')} ({doc_id})",
                "body": _noise_body(aid, aname, doc_type, n),
            }
        )
        n += 1

    # Stable shuffle so Meridian isn't only at the top of every file listing
    head, rest = docs[:10], docs[10:]
    rng.shuffle(rest)
    return head + rest


def main() -> None:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    documents = build_documents(target=target)

    gen.BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    # Clear old noise PDFs but keep folder
    for old in gen.BRONZE_DIR.glob("*.pdf"):
        old.unlink()

    manifest = []
    force_meta_path = ROOT / "bronze" / "force_meta.jsonl"
    force_lines = []

    for doc in documents:
        path = gen.BRONZE_DIR / doc["filename"]
        gen.write_pdf(path, doc["title"], doc["body"])
        manifest.append(
            {
                "doc_id": doc["doc_id"],
                "filename": doc["filename"],
                "relative_path": f"bronze/documents/{doc['filename']}",
                "doc_type": doc["doc_type"],
                "account_id": doc["account_id"],
                "account_name": doc["account_name"],
                "effective_date": doc["effective_date"],
                "source_system": doc["source_system"],
                "title": doc["title"],
            }
        )
        if "force_quality" in doc or "force_parse" in doc:
            force_lines.append(
                {
                    "doc_id": doc["doc_id"],
                    "force_quality": doc.get("force_quality"),
                    "force_parse": doc.get("force_parse"),
                }
            )
        print(f"wrote {path.name}")

    manifest_path = ROOT / "bronze" / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for row in manifest:
            f.write(__import__("json").dumps(row) + "\n")
    with force_meta_path.open("w", encoding="utf-8") as f:
        for row in force_lines:
            f.write(__import__("json").dumps(row) + "\n")

    print(f"manifest → {manifest_path} ({len(manifest)} docs)")
    print(f"force_meta → {force_meta_path} ({len(force_lines)} quarantine hooks)")


if __name__ == "__main__":
    main()
