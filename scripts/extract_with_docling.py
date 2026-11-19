#!/usr/bin/env python3
"""Bronze → Silver: parse financial PDFs with Docling, emit governed artifacts.

Medallion mapping (see article + README):
  Bronze  — raw PDFs + catalog manifest (URI, hash, mime, provenance)
  Silver  — Docling markdown + enriched metadata JSON (parsed, quality-scored)
  Gold    — built later in dbt (structured facts + knowledge_base / search)

Also refreshes dbt seeds so the warehouse catalog and document bodies stay
in sync with whatever was just extracted.
"""

from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRONZE_DIR = ROOT / "bronze" / "documents"
MANIFEST = ROOT / "bronze" / "manifest.jsonl"
FORCE_META = ROOT / "bronze" / "force_meta.jsonl"
SILVER_DIR = ROOT / "silver" / "extracted"
SEEDS = ROOT / "seeds"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> list[dict]:
    rows = []
    with MANIFEST.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_force_meta() -> dict[str, dict]:
    """Optional quarantine hooks from expand_corpus.py (force quality / parse)."""
    if not FORCE_META.exists():
        return {}
    out: dict[str, dict] = {}
    with FORCE_META.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out[row["doc_id"]] = row
    return out


def extract_one(pdf_path: Path) -> tuple[str, dict]:
    """Return (markdown_text, docling_meta). Falls back to a text scrape if Docling missing."""
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        md = result.document.export_to_markdown()
        pages = None
        for attr in ("num_pages", "page_count", "pages"):
            val = getattr(result.document, attr, None)
            if val is None or callable(val):
                continue
            try:
                pages = len(val) if not isinstance(val, (int, float)) else int(val)
            except TypeError:
                pages = None
            break
        meta = {
            "extractor": "docling",
            "docling_version": getattr(
                sys.modules.get("docling"), "__version__", "unknown"
            ),
            "pages": pages,
            "parse_status": "ok",
        }
        return md, meta
    except ImportError:
        # Lightweight fallback so the demo still runs before `pip install docling`.
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            pages = [p.extract_text() or "" for p in reader.pages]
            md = "\n\n".join(pages)
            return md, {
                "extractor": "pypdf_fallback",
                "pages": len(pages),
                "parse_status": "fallback",
            }
        except ImportError:
            # Last resort: embed generator body is not available; read nothing useful.
            return (
                f"[extraction unavailable for {pdf_path.name} — install docling or pypdf]",
                {
                    "extractor": "none",
                    "pages": None,
                    "parse_status": "failed",
                },
            )


def quality_score(text: str, meta: dict) -> float:
    if meta.get("parse_status") == "failed":
        return 0.0
    if not text or len(text.strip()) < 40:
        return 0.2
    # Crude but demo-useful: reward length + presence of financial cues.
    cues = sum(
        1
        for token in (
            "USD",
            "covenant",
            "invoice",
            "leverage",
            "liquidity",
            "ACC-",
            "payable",
            "receivable",
        )
        if token.lower() in text.lower()
    )
    base = 0.55 if meta.get("extractor") == "docling" else 0.45
    return round(min(0.99, base + 0.05 * cues + min(0.2, len(text) / 5000)), 2)


def detect_sensitivity(text: str) -> str:
    # Toy policy tags for the Silver governance gate.
    lowered = text.lower()
    if "ssn" in lowered or re.search(r"\b\d{3}-\d{2}-\d{4}\b", text):
        return "restricted_pii"
    if "covenant" in lowered or "credit committee" in lowered:
        return "confidential"
    if "10-q" in lowered or "earnings call" in lowered:
        return "public_market"
    return "internal"


def write_seeds(catalog_rows: list[dict], body_rows: list[dict]) -> None:
    SEEDS.mkdir(parents=True, exist_ok=True)

    catalog_fields = [
        "doc_id",
        "filename",
        "relative_path",
        "uri",
        "doc_type",
        "account_id",
        "account_name",
        "effective_date",
        "source_system",
        "title",
        "mime_type",
        "byte_size",
        "content_sha256",
        "ingested_at",
        "bronze_layer",
    ]
    with (SEEDS / "raw_document_catalog.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=catalog_fields)
        w.writeheader()
        for row in catalog_rows:
            w.writerow({k: row.get(k, "") for k in catalog_fields})

    body_fields = [
        "doc_id",
        "account_id",
        "doc_type",
        "title",
        "effective_date",
        "source_system",
        "extractor",
        "parse_status",
        "quality_score",
        "sensitivity_label",
        "page_count",
        "content_sha256",
        "extracted_at",
        "body_markdown",
        "citation_url",
    ]
    with (SEEDS / "raw_document_bodies.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=body_fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for row in body_rows:
            w.writerow({k: row.get(k, "") for k in body_fields})

    # Lightweight account dim for joins / narrative demos
    accounts = {}
    for row in catalog_rows:
        accounts[row["account_id"]] = row["account_name"]
    with (SEEDS / "dim_accounts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["account_id", "account_name", "sector"])
        w.writeheader()
        sector = {
            "ACC-8847": "industrials",
            "ACC-1102": "consumer_staples",
            "ACC-3301": "transportation",
            "ACC-2201": "materials",
            "ACC-4402": "consumer_discretionary",
            "ACC-5503": "utilities",
            "ACC-6604": "technology",
            "ACC-7705": "consumer_staples",
            "ACC-8806": "transportation",
            "ACC-9907": "industrials",
            "ACC-1010": "health_care",
            "ACC-1111": "real_estate",
        }
        for aid, name in sorted(accounts.items()):
            w.writerow(
                {
                    "account_id": aid,
                    "account_name": name,
                    "sector": sector.get(aid, "other"),
                }
            )


def main() -> None:
    if not MANIFEST.exists():
        print("No bronze/manifest.jsonl — run scripts/generate_sample_pdfs.py first", file=sys.stderr)
        sys.exit(1)

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    force_meta = load_force_meta()
    catalog_rows: list[dict] = []
    body_rows: list[dict] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for entry in manifest:
        pdf_path = BRONZE_DIR / entry["filename"]
        if not pdf_path.exists():
            print(f"missing PDF: {pdf_path}", file=sys.stderr)
            continue

        digest = sha256_file(pdf_path)
        mime = mimetypes.guess_type(pdf_path.name)[0] or "application/pdf"
        md, meta = extract_one(pdf_path)
        hook = force_meta.get(entry["doc_id"], {})
        if hook.get("force_parse"):
            meta = {**meta, "parse_status": hook["force_parse"]}
        q = quality_score(md, meta)
        if hook.get("force_quality") is not None:
            q = float(hook["force_quality"])
        sensitivity = detect_sensitivity(md)

        md_path = SILVER_DIR / f"{entry['doc_id']}.md"
        json_path = SILVER_DIR / f"{entry['doc_id']}.json"
        md_path.write_text(md, encoding="utf-8")

        silver_record = {
            **entry,
            "content_sha256": digest,
            "mime_type": mime,
            "byte_size": pdf_path.stat().st_size,
            "extracted_at": now,
            "extractor": meta.get("extractor"),
            "parse_status": meta.get("parse_status"),
            "page_count": meta.get("pages"),
            "quality_score": q,
            "sensitivity_label": sensitivity,
            "markdown_path": str(md_path.relative_to(ROOT)),
            "body_preview": md[:280].replace("\n", " "),
        }
        json_path.write_text(json.dumps(silver_record, indent=2), encoding="utf-8")

        catalog_rows.append(
            {
                **entry,
                "uri": f"file://{pdf_path.resolve()}",
                "mime_type": mime,
                "byte_size": pdf_path.stat().st_size,
                "content_sha256": digest,
                "ingested_at": now,
                "bronze_layer": "physical_copy",
            }
        )
        # Single-line CSV for BigQuery seeds (no allow_quoted_newlines on dbt seed).
        # Restore newlines in silver_document_bodies via replace('\\n', '\n').
        body_flat = re.sub(r"[ \t]+", " ", md)
        body_flat = re.sub(r"\n{3,}", "\n\n", body_flat).strip()
        body_flat = body_flat.replace("\\", "\\\\").replace("\n", "\\n")
        body_rows.append(
            {
                "doc_id": entry["doc_id"],
                "account_id": entry["account_id"],
                "doc_type": entry["doc_type"],
                "title": entry["title"],
                "effective_date": entry["effective_date"],
                "source_system": entry["source_system"],
                "extractor": meta.get("extractor"),
                "parse_status": meta.get("parse_status"),
                "quality_score": q,
                "sensitivity_label": sensitivity,
                "page_count": meta.get("pages") or "",
                "content_sha256": digest,
                "extracted_at": now,
                "body_markdown": body_flat,
                "citation_url": f"folio://{entry['doc_type']}/{entry['doc_id']}",
            }
        )
        print(
            f"{entry['doc_id']}: {meta.get('extractor')} "
            f"quality={q} sensitivity={sensitivity} → {md_path.name}"
        )

    write_seeds(catalog_rows, body_rows)
    print(f"seeds refreshed under {SEEDS}")
    print("Silver gate complete. Next: dbt seed && dbt build")


if __name__ == "__main__":
    main()
