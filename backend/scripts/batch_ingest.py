"""
Batch ingest all documents that have ingested_at = NULL into Pinecone.
Run from backend/ with: python scripts/batch_ingest.py
"""
import asyncio
import os
import sys
import tempfile
import traceback
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.models.models import Document
from app.core.knowledge_base import get_knowledge_base
from app.utils.document_processor import get_document_processor
from sqlalchemy import select
from loguru import logger


async def ingest_one(db, doc: Document, kb, processor) -> dict:
    file_bytes = None

    # Resolve cloud_file_id: from metadata or from drive:// file_path prefix
    meta = doc.metadata_json or {}
    cloud_file_id = meta.get("cloud_file_id")
    if not cloud_file_id and doc.file_path and str(doc.file_path).startswith("drive://"):
        cloud_file_id = str(doc.file_path)[len("drive://"):]

    if cloud_file_id:
        try:
            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            file_bytes = storage.download_file(cloud_file_id)
        except Exception as e:
            logger.warning(f"  Cloud download failed for {doc.file_name}: {e}")

    # Fallback: local file path
    if not file_bytes and doc.file_path:
        local_path = str(doc.file_path)
        if local_path.startswith("drive://"):
            pass  # already tried above
        else:
            if not os.path.isabs(local_path):
                local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), local_path)
            if os.path.exists(local_path):
                with open(local_path, "rb") as f:
                    file_bytes = f.read()

    if not file_bytes:
        return {"status": "skip", "reason": "no file source"}

    # Write to temp — ensure extension is present so processor can detect format.
    # Detect by magic bytes when the filename has no extension (Google Workspace exports).
    fname = doc.file_name
    if not os.path.splitext(fname)[1]:
        if file_bytes[:4] == b"PK\x03\x04":
            fname += ".xlsx"   # ZIP-based: xlsx/docx — treat as xlsx for Google Sheets
        else:
            fname += ".pdf"    # Default for Google Docs / Presentations
    suffix = f"_{fname}"[-50:]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(file_bytes)
    tmp.close()

    try:
        processed = processor.process_document(
            tmp.name,
            additional_metadata={
                "twg_id": str(doc.twg_id) if doc.twg_id else "general",
                "doc_id": str(doc.id),
                "file_name": doc.file_name,
            }
        )
    finally:
        try:
            os.remove(tmp.name)
        except Exception:
            pass

    if processed["status"] != "success":
        return {"status": "error", "reason": processed.get("error", "unknown")}

    chunks = processed.get("chunks", [])
    if not chunks:
        return {"status": "skip", "reason": "no text extracted"}

    documents = [
        {"id": f"{doc.id}_chunk_{i}", "text": c["text"], "metadata": c["metadata"]}
        for i, c in enumerate(chunks)
    ]

    namespace = f"twg-{doc.twg_id}" if doc.twg_id else "twg-general"
    result = kb.upsert_documents(documents=documents, namespace=namespace)

    doc.ingested_at = datetime.utcnow()
    await db.commit()

    return {"status": "ok", "chunks": result.get("total_upserted", 0), "namespace": namespace}


async def main():
    kb = get_knowledge_base()
    processor = get_document_processor()

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Document).where(Document.ingested_at == None))
        docs = res.scalars().all()
        logger.info(f"Found {len(docs)} uningested documents")

        ok = skip = err = 0
        for doc in docs:
            logger.info(f"→ {doc.file_name[:60]}")
            try:
                result = await ingest_one(db, doc, kb, processor)
                status = result["status"]
                if status == "ok":
                    ok += 1
                    logger.success(f"  ✓ {result['chunks']} chunks → {result['namespace']}")
                elif status == "skip":
                    skip += 1
                    logger.warning(f"  ⚠ skipped: {result['reason']}")
                else:
                    err += 1
                    logger.error(f"  ✗ error: {result['reason']}")
            except Exception as e:
                err += 1
                logger.error(f"  ✗ exception: {e}")
                traceback.print_exc()

        logger.info(f"\nDone: {ok} ingested, {skip} skipped, {err} errors")


if __name__ == "__main__":
    asyncio.run(main())
