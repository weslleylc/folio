#!/usr/bin/env python3
"""Print the Meridian demo tables — useful during a live walkthrough."""

from __future__ import annotations

from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "folio.duckdb"


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)

    print("\n=== Gold account risk rollup (Meridian should stand out) ===")
    print(
        con.execute(
            """
            select account_id, account_name, document_count, past_due_docs,
                   covenant_docs, liquidity_docs, max_leverage_mentioned, max_risk_tier
            from gold_account_risk_rollup
            order by case when account_id = 'ACC-8847' then 0 else 1 end
            """
        )
        .fetchdf()
        .to_string(index=False)
    )

    print("\n=== Meridian narrative (Bronze/Silver/Gold timeline) ===")
    print(
        con.execute(
            """
            with meridian as (select 'ACC-8847' as account_id),
            catalog as (
                select cast(effective_date as timestamp) as occurred_at,
                       'bronze_catalog' as source, doc_id as artifact_id,
                       left(title, 80) as snippet
                from bronze_document_catalog
                where account_id = (select account_id from meridian)
            ),
            gold_facts as (
                select cast(effective_date as timestamp) as occurred_at,
                       'gold_fact' as source, doc_id as artifact_id,
                       'tier=' || risk_signal_tier
                         || ' covenant=' || cast(flag_covenant_language as varchar)
                         || ' liquidity=' || cast(flag_liquidity_language as varchar) as snippet
                from gold_document_facts
                where account_id = (select account_id from meridian)
            )
            select * from catalog
            union all select * from gold_facts
            order by occurred_at, source
            """
        )
        .fetchdf()
        .to_string(index=False)
    )

    try:
        n = con.execute("select count(*) from knowledge_base").fetchone()[0]
        print(f"\n=== knowledge_base rows: {n} ===")
        print(
            con.execute(
                """
                select classification, count(*) as chunks
                from documents_embedded_classified
                group by 1 order by chunks desc
                """
            )
            .fetchdf()
            .to_string(index=False)
        )
    except duckdb.CatalogException:
        print("\n(knowledge_base not built — run: make build-ai)")


if __name__ == "__main__":
    main()
