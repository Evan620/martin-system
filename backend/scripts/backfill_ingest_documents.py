"""
Backfill ingestion for registry documents that were uploaded but never
ingested into the vector store (Document.ingested_at IS NULL).

WHY THIS EXISTS
    Documents uploaded before auto-ingestion (or whose ingestion failed
    silently) are listed in the registry but are invisible to Martin's
    retrieve_document_content RAG tool, because they have no chunks in
    Pinecone. This script finds every such document and pushes it through
    the EXACT same ingestion path as POST /documents/{id}/ingest — it calls
    app.api.routes.documents.ingest_document directly rather than
    re-implementing the download → process → chunk → upsert pipeline, so
    the two paths can never drift.

PINECONE NAMESPACE BEHAVIOR (mirrors the API route)
    Each document's chunks are upserted into a namespace derived from its
    TWG ownership:

        twg-{twg_id}   when the document belongs to a TWG
        twg-general    when the document is global (twg_id IS NULL)

    These are the same namespaces retrieve_document_content queries at
    answer time (twg-{twg_id} for a member's TWG, twg-general otherwise),
    so a backfilled document becomes retrievable immediately, with the
    same TWG scoping the registry enforces.

SAFETY
    - DRY-RUN IS THE DEFAULT. Without --execute, the script only PRINTS
      what would be ingested (id, file_name, twg/global, size) and exits.
      It never touches Pinecone or writes to the DB in dry-run mode.
    - --execute is required to actually ingest.
    - If DATABASE_URL points at Railway production, --allow-prod must
      ALSO be passed; otherwise the script refuses to execute.
    - Ingestion is idempotent at the vector level: chunk ids are
      "{doc_id}_chunk_{i}", so re-running upserts (overwrites) the same
      vectors rather than duplicating them.
    - The acting user must be an ADMIN (route enforces TWG/confidential
      access checks; admins pass all of them). Pick a specific account
      with --as-email if needed.

USAGE
    PYTHONPATH=. python scripts/backfill_ingest_documents.py                 # dry-run (default)
    PYTHONPATH=. python scripts/backfill_ingest_documents.py --limit 5       # dry-run, first 5
    PYTHONPATH=. python scripts/backfill_ingest_documents.py --execute       # actually ingest
    PYTHONPATH=. python scripts/backfill_ingest_documents.py --execute --limit 10 --as-email ops@africacen.org
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Document, User, UserRole


def _doc_size(doc: Document) -> str:
    """Best-effort human-readable size: metadata, then local file, else '?'."""
    metadata = doc.metadata_json or {}
    size = metadata.get("file_size") or metadata.get("size")
    if not size and doc.file_path:
        try:
            if os.path.exists(doc.file_path):
                size = os.path.getsize(doc.file_path)
        except OSError:
            size = None
    if not size:
        return "?"
    try:
        size = int(size)
    except (TypeError, ValueError):
        return str(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return "?"


def _scope_label(doc: Document) -> str:
    return f"twg-{doc.twg_id}" if doc.twg_id else "global (twg-general)"


async def _list_pending(limit: Optional[int]) -> list:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Document)
            .where(Document.ingested_at.is_(None))
            .order_by(Document.created_at.asc())
        )
        if limit:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _get_acting_admin(email: Optional[str]) -> User:
    async with AsyncSessionLocal() as session:
        if email:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                print(f"❌ No user found with email {email}")
                sys.exit(2)
            if user.role != UserRole.ADMIN:
                print(f"❌ {email} is not an ADMIN (role={user.role}); refusing.")
                sys.exit(2)
            return user
        result = await session.execute(
            select(User)
            .where(User.role == UserRole.ADMIN, User.is_active == True)  # noqa: E712
            .order_by(User.created_at.asc())
            .limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            print("❌ No active ADMIN user found; pass --as-email explicitly.")
            sys.exit(2)
        return user


async def main(execute: bool, limit: Optional[int], as_email: Optional[str], allow_prod: bool) -> None:
    db_url = settings.DATABASE_URL
    is_prod = "railway.internal" in db_url or "rlwy.net" in db_url
    print(f"\n=== Backfill document ingestion ===")
    print(f"DB:   {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"Mode: {'EXECUTE' if execute else 'DRY RUN (default — pass --execute to ingest)'}\n")

    if execute and is_prod and not allow_prod:
        print("❌ REFUSING: DATABASE_URL points at Railway production.")
        print("   Re-run with --allow-prod if this is intentional.\n")
        sys.exit(2)

    docs = await _list_pending(limit)
    if not docs:
        print("Nothing to do: no documents with ingested_at IS NULL.\n")
        return

    print(f"Found {len(docs)} document(s) pending ingestion:\n")
    for i, doc in enumerate(docs, 1):
        print(
            f"[{i:3d}/{len(docs)}] {str(doc.id)}  "
            f"{doc.file_name[:45]:45s}  {_scope_label(doc):50s}  {_doc_size(doc)}"
        )

    if not execute:
        print("\nDry run complete. Nothing was ingested. Pass --execute to ingest.\n")
        return

    # Reuse the API route handler itself — same download/process/upsert path,
    # same twg-{twg_id} / twg-general namespacing, same ingested_at stamping.
    from app.api.routes.documents import ingest_document

    acting_user = await _get_acting_admin(as_email)
    print(f"\nActing as: {acting_user.email} (ADMIN)\n")

    ok, failed = 0, 0
    for i, doc in enumerate(docs, 1):
        print(f"[{i:3d}/{len(docs)}] ingesting {doc.file_name[:60]} …")
        try:
            # Fresh session per document so one failure cannot poison the rest.
            async with AsyncSessionLocal() as session:
                result = await ingest_document(
                    doc_id=doc.id, current_user=acting_user, db=session
                )
            print(
                f"            ✓ {result.get('chunks_ingested', '?')} chunks → "
                f"namespace {result.get('namespace', '?')}"
            )
            ok += 1
        except HTTPException as e:
            print(f"            ⚠ HTTP {e.status_code}: {e.detail}")
            failed += 1
        except Exception as e:  # noqa: BLE001 — operator script, keep going
            print(f"            ⚠ {type(e).__name__}: {str(e)[:140]}")
            failed += 1

    print(f"\nDone. ingested={ok} failed={failed} total={len(docs)}\n")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill Pinecone ingestion for documents with ingested_at IS NULL."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be ingested (this is already the default mode)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually ingest (without this flag the script only prints)",
    )
    parser.add_argument("--limit", type=int, default=None, help="process at most N documents")
    parser.add_argument(
        "--as-email", default=None, help="ADMIN user to act as (default: first active admin)"
    )
    parser.add_argument(
        "--allow-prod",
        action="store_true",
        help="required in addition to --execute when DATABASE_URL is Railway production",
    )
    args = parser.parse_args()

    if args.dry_run and args.execute:
        print("❌ --dry-run and --execute are mutually exclusive.")
        sys.exit(2)

    asyncio.run(main(args.execute, args.limit, args.as_email, args.allow_prod))
