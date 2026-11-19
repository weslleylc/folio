#!/usr/bin/env python3
"""Land "batch 2" into the Bronze seeds — simulates new files arriving after the first load.

Bronze is an append-only log (models/bronze/bronze_document_versions.sql). Batch 2 exercises
the two cases that matter for governance:

  1. A NEW VERSION of an existing document — same doc_id (INV-4401), different bytes/sha256.
     Bronze keeps v1 and registers v2; Silver / Gold read only the current version.
  2. An EXACT DUPLICATE under a new name — MER-X02 re-sent by e-mail (identical bytes, so the
     same sha256). Bronze registers it (provenance is real); Silver quarantines it as a duplicate.

Idempotent: re-running replaces any earlier batch-2 rows. Run after expand_corpus.py +
extract_with_docling.py (batch 1).

  python scripts/ingest_batch2.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import extract_with_docling as ex  # noqa: E402

_spec = importlib.util.spec_from_file_location("generate_sample_pdfs", ROOT / "scripts" / "generate_sample_pdfs.py")
gen = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(gen)

BATCH = 2
V2_DIR = ex.BRONZE_DIR / "v2"

INV_4401_V2_BODY = [
    "Vendor: AlloyForge Materials LLC",
    "Bill-to: Meridian Industrial Corp (ACC-8847)",
    "Invoice date: 2025-07-15",
    "Due date: 2025-08-14",
    "Status: PAST DUE - 84 days overdue as of 2025-11-07. Credit hold now in effect.",
    "",
    "## Line items",
    "Hot-rolled steel coil lot AF-8821 .... USD 184,500.00",
    "Freight surcharge ........................ USD 6,200.00",
    "Late fee (1.5% per month) ............... USD 5,310.00",
    "Total due ............................... USD 196,010.00",
    "",
    "## Collections notice",
    "Third and final notice. Accounts receivable for Meridian Industrial Corp has aged well",
    "beyond net-30 terms and the account is on credit hold. Revised statement supersedes the",
    "2025-09-12 notice. Reference PO MI-77821 and ACC-8847 on the remittance.",
    "Please contact [collections desk] regarding Meridian's payment plan.",
]


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _entry_to_rows(entry: dict, pdf: Path, uri_path: Path, now: str) -> tuple[dict, dict, str]:
    digest = ex.sha256_file(pdf)
    md, meta = ex.extract_one(pdf)
    quality = ex.quality_score(md, meta)
    sensitivity = ex.detect_sensitivity(md)
    catalog = {
        **entry,
        "relative_path": str(pdf.relative_to(ROOT)),
        "filename": pdf.name,
        "uri": f"file://{uri_path.resolve()}",
        "mime_type": "application/pdf",
        "byte_size": pdf.stat().st_size,
        "content_sha256": digest,
        "ingested_at": now,
        "bronze_layer": "physical_copy",
        "ingest_batch": BATCH,
    }
    body = {
        "doc_id": entry["doc_id"],
        "account_id": entry["account_id"],
        "doc_type": entry["doc_type"],
        "title": entry["title"],
        "effective_date": entry["effective_date"],
        "source_system": entry["source_system"],
        "extractor": meta.get("extractor"),
        "parse_status": meta.get("parse_status"),
        "quality_score": quality,
        "sensitivity_label": sensitivity,
        "page_count": meta.get("pages") or "",
        "content_sha256": digest,
        "extracted_at": now,
        "body_markdown": ex.flatten_for_seed(md),
        "citation_url": f"folio://{entry['doc_type']}/{entry['doc_id']}",
    }
    return catalog, body, md


def main() -> None:
    cat_path = ex.SEEDS / "raw_document_catalog.csv"
    body_path = ex.SEEDS / "raw_document_bodies.csv"
    catalog = [r for r in _read(cat_path) if str(r.get("ingest_batch") or "1") == "1"]
    by_id = {r["doc_id"]: r for r in catalog}
    for needed in ("INV-4401", "MER-X02"):
        if needed not in by_id:
            sys.exit(f"{needed} not found in batch 1 — run expand_corpus.py + extract_with_docling.py first")

    # Drop any earlier batch-2 rows (idempotent), keep batch 1 untouched.
    old_later_shas = {r["content_sha256"] for r in _read(cat_path) if str(r.get("ingest_batch") or "1") != "1"}
    bodies = [r for r in _read(body_path) if r["content_sha256"] not in old_later_shas]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_cat: list[dict] = []
    new_bodies: list[dict] = []

    # 1) New version of INV-4401 (same doc_id, new bytes).
    base = by_id["INV-4401"]
    V2_DIR.mkdir(parents=True, exist_ok=True)
    v2_pdf = V2_DIR / base["filename"]
    gen.write_pdf(v2_pdf, base["title"].replace("(PAST DUE)", "(PAST DUE - revised)"), INV_4401_V2_BODY)
    entry = {k: base[k] for k in ("doc_id", "doc_type", "account_id", "account_name", "source_system")}
    entry.update({"title": base["title"].replace("(PAST DUE)", "(PAST DUE - revised)"), "effective_date": "2025-11-07"})
    c, b, md = _entry_to_rows(entry, v2_pdf, v2_pdf, now)
    new_cat.append(c)
    new_bodies.append(b)
    (ex.SILVER_DIR / "INV-4401.v2.md").write_text(md, encoding="utf-8")

    # 2) Exact duplicate of MER-X02, arriving through a different channel.
    src = by_id["MER-X02"]
    dup_pdf = ex.BRONZE_DIR / "MER-X02-DUP_email_resend.pdf"
    shutil.copyfile(ex.BRONZE_DIR / src["filename"], dup_pdf)
    entry = {k: src[k] for k in ("doc_type", "account_id", "account_name", "effective_date")}
    entry.update(
        {
            "doc_id": "MER-X02-DUP",
            "source_system": "email_inbox",
            "title": "RE: " + src["title"] + " (re-sent copy)",
        }
    )
    c, b, md = _entry_to_rows(entry, dup_pdf, dup_pdf, now)
    new_cat.append(c)
    new_bodies.append(b)
    (ex.SILVER_DIR / "MER-X02-DUP.md").write_text(md, encoding="utf-8")

    cat_fields = list(_read(cat_path)[0].keys())
    if "ingest_batch" not in cat_fields:
        cat_fields.append("ingest_batch")
    for r in catalog:
        r["ingest_batch"] = 1
    with cat_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cat_fields)
        w.writeheader()
        for row in catalog + new_cat:
            w.writerow({k: row.get(k, "") for k in cat_fields})

    body_fields = list(bodies[0].keys())
    import csv as _csv

    with body_path.open("w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=body_fields, quoting=_csv.QUOTE_ALL)
        w.writeheader()
        for row in bodies + new_bodies:
            w.writerow({k: row.get(k, "") for k in body_fields})

    print(json.dumps({"batch": BATCH, "new_catalog_rows": len(new_cat), "docs": [r["doc_id"] for r in new_cat]}))
    for r in new_cat:
        print(f"  {r['doc_id']:<14} sha256={r['content_sha256'][:12]}… via {r['source_system']}")
    print("Next: dbt seed && dbt build --vars '{\"bronze_max_batch\": 2}'")


if __name__ == "__main__":
    main()
