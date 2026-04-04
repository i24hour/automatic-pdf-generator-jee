"""
Delete old SharedPDF records before a cutoff date.

Usage:
  DATABASE_URL=... python3 backend/cleanup_shared_pdfs.py --before 2026-04-03
  DATABASE_URL=... python3 backend/cleanup_shared_pdfs.py --before 2026-04-03 --apply
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, text


def normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url


def parse_cutoff(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete SharedPDF rows before a cutoff date.")
    parser.add_argument("--before", required=True, help="Delete rows with created_at before this ISO date/datetime.")
    parser.add_argument("--apply", action="store_true", help="Actually delete rows. Default is dry-run.")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    cutoff = parse_cutoff(args.before)
    engine = create_engine(normalize_database_url(database_url))

    preview_sql = text(
        """
        select
          count(*) as total_rows,
          count(*) filter (where pdf_url = 'pending') as pending_rows,
          count(*) filter (where pdf_url like 'https://storage.googleapis.com/%' or pdf_url like 'gs://%') as gcs_rows,
          count(*) filter (where visibility = 'public') as public_rows,
          count(*) filter (where visibility = 'private') as private_rows,
          count(*) filter (where visibility = 'unlisted') as unlisted_rows
        from shared_pdfs
        where created_at < :cutoff
        """
    )
    delete_sql = text("delete from shared_pdfs where created_at < :cutoff")

    with engine.begin() as conn:
        preview = conn.execute(preview_sql, {"cutoff": cutoff}).mappings().one()
        print(f"Cutoff UTC: {cutoff.isoformat()}")
        print(dict(preview))

        if not args.apply:
            print("Dry run only. Re-run with --apply to delete.")
            return 0

        result = conn.execute(delete_sql, {"cutoff": cutoff})
        print(f"Deleted rows: {result.rowcount}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
