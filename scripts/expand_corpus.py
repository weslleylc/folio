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


def _noise_body(account_id: str, account_name: str, doc_type: str, idx: int) -> list[str]:
    """Boilerplate without Meridian risk keywords (covenant / past due / liquidity / DSO).

    Gold flags are regex over those phrases — noise must stay 'clean' so Meridian
    still stands out on the rollup chart.
    """
    amt = 10_000 + (idx * 137) % 90_000
    return [
        f"Account: {account_name} ({account_id})",
        f"Document sequence: NOISE-{idx:03d}",
        f"Doc type: {doc_type}",
        "",
        "## Summary",
        f"Routine {doc_type.replace('_', ' ')} for {account_name}. Operations are stable.",
        f"Reference amount USD {amt:,}.00. Balance settled on schedule.",
        "",
        "## Notes",
        "Internal filing copy for the demo corpus. No watchlist items on this account.",
        "This document is unrelated to Meridian Industrial ACC-8847.",
        "Collections status: CURRENT.",
    ]


def _meridian_extra(idx: int) -> tuple[str, str, list[str]]:
    """Extra Meridian signal docs so the story still dominates search/rollup."""
    variants = [
        (
            "invoice",
            "Past-due notice — secondary supplier",
            [
                "Vendor: RiverBend Coatings",
                "Bill-to: Meridian Industrial Corp (ACC-8847)",
                "Status: PAST DUE / OVERDUE — credit hold warning",
                "",
                "## Collections",
                "Meridian AP stretch continues. Open balance USD 28,400.00.",
                "Reference ACC-8847. Payment plan requested; working capital pressure noted.",
            ],
        ),
        (
            "credit_memo",
            "Monitoring update — covenant headroom",
            [
                "Subject account: Meridian Industrial Corp (ACC-8847)",
                "",
                "## Update",
                "Interim leverage certificate printed 3.55x against 3.75x amended covenant.",
                "Limited headroom. Continue weekly cash reporting and DSO remediation.",
                "Event of default risk rises if leverage exceeds 3.60x on next certificate.",
            ],
        ),
        (
            "analyst_note",
            "Flash note — liquidity watch",
            [
                "Issuer: Meridian Industrial (ACC-8847)",
                "",
                "## Takeaway",
                "Liquidity and days sales outstanding remain the key watch items.",
                "Covenant amendment bought time; cash conversion still thin into year-end.",
            ],
        ),
    ]
    doc_type, title_suffix, body = variants[idx % len(variants)]
    return doc_type, title_suffix, body


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
    docs = [dict(d) for d in gen.DOCUMENTS]  # original Meridian + 3 noise
    # Extra Meridian signal
    for i in range(8):
        doc_type, suffix, body = _meridian_extra(i)
        doc_id = f"MER-X{i+1:02d}"
        docs.append(
            {
                "doc_id": doc_id,
                "filename": f"{doc_id}_{doc_type}.pdf",
                "doc_type": doc_type,
                "account_id": "ACC-8847",
                "account_name": "Meridian Industrial Corp",
                "effective_date": f"2025-{(9 + i % 3):02d}-{(5 + i):02d}",
                "source_system": SOURCES[doc_type],
                "title": f"{suffix} — Meridian ({doc_id})",
                "body": body,
            }
        )

    docs.extend(_quarantine_docs())

    rng = random.Random(42)
    n = 1
    while len(docs) < target:
        aid, aname, _sector = ACCOUNTS[n % len(ACCOUNTS)]
        if aid == "ACC-8847" and n % 5 != 0:
            # mostly noise on other accounts
            aid, aname, _sector = ACCOUNTS[(n + 3) % len(ACCOUNTS)]
            if aid == "ACC-8847":
                aid, aname, _sector = ACCOUNTS[1]
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
                "title": f"{aname} {doc_type.replace('_', ' ')} {doc_id}",
                "body": _noise_body(aid, aname, doc_type, n),
            }
        )
        n += 1
        if n > 500:
            break

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
