#!/usr/bin/env python3
"""Generate sample financial PDFs for the Folio demo (Bronze landing zone).

Story: Meridian Industrial (ACC-8847) - working-capital stress and covenant
headroom erosion across Q3-Q4 2025, scattered across invoices, a credit
facility amendment, a credit-committee memo, an earnings call excerpt,
an MD&A section, and an analyst note. Noise documents for other accounts
keep exact-match joins from being enough.
"""

from __future__ import annotations

import json
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
BRONZE_DIR = ROOT / "bronze" / "documents"


class DocPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _ascii(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    usable = pdf.epw  # explicit width avoids "not enough horizontal space"
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(usable, 8, _ascii(title))
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        line = _ascii(line)
        pdf.set_x(pdf.l_margin)
        if line.startswith("## "):
            pdf.ln(3)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(usable, 7, line[3:])
            pdf.set_font("Helvetica", size=11)
        elif line.startswith("# "):
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(usable, 7, line[2:])
            pdf.set_font("Helvetica", size=11)
        elif line.strip() == "":
            pdf.ln(3)
        else:
            pdf.multi_cell(usable, 6, line)
    pdf.output(str(path))


DOCUMENTS: list[dict] = [
    {
        "doc_id": "INV-4401",
        "filename": "INV-4401_AlloyForge_past_due.pdf",
        "doc_type": "invoice",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-09-12",
        "source_system": "ap_portal",
        "title": "Invoice INV-4401 - AlloyForge Materials (PAST DUE)",
        "body": [
            "Vendor: AlloyForge Materials LLC",
            "Bill-to: Meridian Industrial Corp (ACC-8847)",
            "Invoice date: 2025-07-15",
            "Due date: 2025-08-14",
            "Status: PAST DUE - 29 days overdue as of 2025-09-12",
            "",
            "## Line items",
            "Hot-rolled steel coil lot AF-8821 .... USD 184,500.00",
            "Freight surcharge ........................ USD 6,200.00",
            "Total due ............................... USD 190,700.00",
            "",
            "## Collections notice",
            "Second notice. Accounts receivable for Meridian Industrial Corp has aged beyond",
            "net-30 terms. AlloyForge will place the account on credit hold if payment is not",
            "received by 2025-09-26. Reference PO MI-77821 and ACC-8847 on the remittance.",
            "Please contact collections@alloyforge.example regarding Meridian's payment plan.",
        ],
    },
    {
        "doc_id": "INV-4412",
        "filename": "INV-4412_NorthRiver_partial.pdf",
        "doc_type": "invoice",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-10-03",
        "source_system": "ap_portal",
        "title": "Invoice INV-4412 - NorthRiver Logistics (Partial payment)",
        "body": [
            "Vendor: NorthRiver Logistics",
            "Bill-to: Meridian Industrial Corp (ACC-8847)",
            "Invoice date: 2025-08-20",
            "Due date: 2025-09-19",
            "Status: PARTIAL - USD 40,000 of USD 92,400 paid",
            "",
            "## Balance",
            "Open balance .............................. USD 52,400.00",
            "Promise-to-pay date from Meridian AP ...... 2025-10-18",
            "",
            "## Note",
            "Meridian Industrial AP indicated cash timing pressure tied to delayed customer",
            "receivables. NorthRiver accepted a short extension for ACC-8847 but will not",
            "extend again without a bank confirmation letter.",
        ],
    },
    {
        "doc_id": "CFA-2025-03",
        "filename": "CFA-2025-03_Meridian_credit_facility_amendment.pdf",
        "doc_type": "credit_facility",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-10-21",
        "source_system": "treasury_vault",
        "title": "Third Amendment to Revolving Credit Agreement - Meridian Industrial",
        "body": [
            "Facility: USD 250,000,000 revolving credit facility",
            "Borrower: Meridian Industrial Corp (ACC-8847)",
            "Agent bank: Harbor Trust Bank",
            "Amendment effective date: 2025-10-21",
            "",
            "## Covenant revisions",
            "Maximum Consolidated Net Leverage Ratio revised from 3.50x to 3.75x through",
            "2026-03-31, stepping back to 3.50x thereafter. Minimum Interest Coverage Ratio",
            "remains 2.50x. Borrower represents that as of 2025-09-30 the leverage ratio was",
            "approximately 3.41x, leaving limited covenant headroom for Meridian Industrial.",
            "",
            "## Conditions precedent",
            "Delivery of a 13-week cash flow forecast satisfactory to the Agent, and evidence",
            "that Meridian has begun collections remediation on receivables aged over 60 days.",
            "Failure to maintain the amended leverage covenant constitutes an Event of Default.",
            "Contact: credit.docs@harbortrust.example referencing ACC-8847 / CFA-2025-03.",
        ],
    },
    {
        "doc_id": "MEMO-CC-991",
        "filename": "MEMO-CC-991_credit_committee_Meridian.pdf",
        "doc_type": "credit_memo",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-10-24",
        "source_system": "credit_risk",
        "title": "Credit Committee Memo CC-991 - Meridian Industrial risk review",
        "body": [
            "Prepared by: Harbor Trust Credit Risk",
            "Subject account: Meridian Industrial Corp (ACC-8847)",
            "Committee date: 2025-10-24",
            "Review period: Q3 2025",
            "",
            "## Recommendation",
            "Approve the third amendment (CFA-2025-03) with heightened monitoring. Meridian's",
            "working-capital cycle lengthened to 74 days from 58 days year-over-year. Supplier",
            "past-due notices (INV-4401, INV-4412) corroborate stretch in payables.",
            "",
            "## Key risks",
            "1. Covenant headroom under 0.35x after the temporary leverage relief.",
            "2. Concentration: top three customers represent 41% of Meridian receivables.",
            "3. Management guidance implies Q4 free cash flow near break-even if collections",
            "   do not improve by mid-November 2025.",
            "",
            "## Monitoring plan",
            "Weekly cash report from Meridian treasury; monthly covenant certificate; escalate",
            "to special assets if leverage prints above 3.60x on any interim certificate.",
        ],
    },
    {
        "doc_id": "EARN-Q3-2025",
        "filename": "EARN-Q3-2025_Meridian_earnings_call_excerpt.pdf",
        "doc_type": "earnings_call",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-11-05",
        "source_system": "ir_transcripts",
        "title": "Meridian Industrial Q3 2025 Earnings Call - Excerpt",
        "body": [
            "Company: Meridian Industrial Corp (ticker: MRDI) - ACC-8847",
            "Call date: 2025-11-05",
            "",
            "## CFO commentary",
            "CFO Dana Okonkwo: Working capital was a headwind this quarter. Days sales",
            "outstanding rose as two large OEM customers pushed payment timing. We are",
            "actively remediating collections and have amended our revolving credit facility",
            "with Harbor Trust to provide temporary leverage covenant headroom through March.",
            "We expect cash conversion to improve in Q4 if those receivables clear as planned.",
            "",
            "## Analyst Q&A",
            "Analyst: How close are you to the leverage covenant after the amendment?",
            "CFO: We printed roughly 3.41x at quarter-end against the amended 3.75x cap. We",
            "have limited headroom and are managing spend carefully. Reference ACC-8847 in",
            "any follow-up with IR.",
        ],
    },
    {
        "doc_id": "10Q-Q3-MDA",
        "filename": "10Q-Q3-2025_Meridian_MDA_liquidity.pdf",
        "doc_type": "sec_filing",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-11-07",
        "source_system": "sec_edgar",
        "title": "Form 10-Q - Management Discussion (Liquidity) - Meridian Industrial",
        "body": [
            "Registrant: Meridian Industrial Corp (ACC-8847)",
            "Period ended: 2025-09-30",
            "Filing date: 2025-11-07",
            "",
            "## Liquidity and Capital Resources",
            "As of September 30, 2025, cash and cash equivalents were USD 41.2 million,",
            "compared with USD 63.8 million at December 31, 2024. The decrease primarily",
            "reflects higher working capital investment and capital expenditures.",
            "",
            "On October 21, 2025, we entered into a third amendment to our revolving credit",
            "agreement increasing the maximum consolidated net leverage ratio to 3.75x through",
            "March 31, 2026. Management believes existing liquidity, together with the amended",
            "facility, is adequate for the next twelve months, though covenant headroom remains",
            "limited if receivables continue to age.",
            "",
            "Trade payables include amounts past contractual due dates with certain suppliers;",
            "see related party and supplier concentration disclosures. Account reference ACC-8847.",
        ],
    },
    {
        "doc_id": "NOTE-ANL-77",
        "filename": "NOTE-ANL-77_sellside_Meridian_covenant.pdf",
        "doc_type": "analyst_note",
        "account_id": "ACC-8847",
        "account_name": "Meridian Industrial Corp",
        "effective_date": "2025-11-08",
        "source_system": "research_desk",
        "title": "Sell-side note ANL-77 - Meridian covenant watch",
        "body": [
            "Desk: Harbor Securities Credit Research",
            "Issuer: Meridian Industrial Corp (ACC-8847 / MRDI)",
            "Date: 2025-11-08",
            "",
            "## Takeaway",
            "We place Meridian Industrial on covenant watch after Q3. The Harbor Trust",
            "amendment buys time, but DSO expansion and supplier stretch (AlloyForge past-due",
            "notice INV-4401) point to cash conversion risk into year-end.",
            "",
            "## What would change our view",
            "Positive: sequential DSO reduction of 8+ days and leverage below 3.20x.",
            "Negative: any interim certificate above 3.60x or a missed supplier commitment.",
            "Clients asking about ACC-8847 should also review CFA-2025-03 and MEMO-CC-991.",
        ],
    },
    # --- noise / other accounts (background) ---
    {
        "doc_id": "INV-2208",
        "filename": "INV-2208_BrightPeak_on_time.pdf",
        "doc_type": "invoice",
        "account_id": "ACC-1102",
        "account_name": "BrightPeak Foods",
        "effective_date": "2025-09-01",
        "source_system": "ap_portal",
        "title": "Invoice INV-2208 - BrightPeak Foods (Paid)",
        "body": [
            "Vendor: GreenField Packaging",
            "Bill-to: BrightPeak Foods (ACC-1102)",
            "Invoice date: 2025-08-01",
            "Due date: 2025-08-31",
            "Status: PAID IN FULL on 2025-08-28",
            "",
            "Routine packaging supply. No collections issues. ACC-1102 remains current.",
        ],
    },
    {
        "doc_id": "CFA-2024-11",
        "filename": "CFA-2024-11_SummitRail_facility.pdf",
        "doc_type": "credit_facility",
        "account_id": "ACC-3301",
        "account_name": "Summit Rail Partners",
        "effective_date": "2024-11-15",
        "source_system": "treasury_vault",
        "title": "Revolving Credit Agreement - Summit Rail Partners",
        "body": [
            "Borrower: Summit Rail Partners (ACC-3301)",
            "Facility size: USD 100,000,000",
            "Maximum leverage covenant: 4.00x",
            "Interest coverage: 2.00x",
            "",
            "Summit Rail remains comfortably inside covenants with leverage at 2.10x.",
            "No amendment activity in 2025. This document is unrelated to Meridian Industrial.",
        ],
    },
    {
        "doc_id": "EARN-Q2-BP",
        "filename": "EARN-Q2-2025_BrightPeak_call.pdf",
        "doc_type": "earnings_call",
        "account_id": "ACC-1102",
        "account_name": "BrightPeak Foods",
        "effective_date": "2025-08-12",
        "source_system": "ir_transcripts",
        "title": "BrightPeak Foods Q2 2025 Earnings Call - Excerpt",
        "body": [
            "Company: BrightPeak Foods (ACC-1102)",
            "CFO: Margin expansion continued. Working capital was a source of cash as",
            "inventory turns improved. No revolving facility draws this quarter.",
            "ACC-1102 guidance unchanged.",
        ],
    },
]


def main() -> None:
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for doc in DOCUMENTS:
        path = BRONZE_DIR / doc["filename"]
        write_pdf(path, doc["title"], doc["body"])
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
        print(f"wrote {path.name}")

    manifest_path = ROOT / "bronze" / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for row in manifest:
            f.write(json.dumps(row) + "\n")
    print(f"manifest → {manifest_path} ({len(manifest)} docs)")


if __name__ == "__main__":
    main()
