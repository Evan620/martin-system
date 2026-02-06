from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(tags=["Debug"])

@router.get("/debug/schema")
async def inspect_schema(db: AsyncSession = Depends(get_db)):
    """
    Inspects the actual database columns for 'twgs' and 'documents' tables.
    Returns a list of columns found in the database.
    """
    try:
        # Check TWGS columns
        twg_result = await db.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'twgs';"
        ))
        twg_columns = [{"name": row[0], "type": row[1]} for row in twg_result.fetchall()]

        # Check DOCUMENTS columns
        doc_result = await db.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'documents';"
        ))
        return {
            "twgs_columns": twg_columns,
            "documents_columns": doc_columns
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/debug/test_twgs")
async def test_twgs(db: AsyncSession = Depends(get_db)):
    """Runs the exact query from list_twgs to capture the error."""
    try:
        from app.models.models import TWG
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        query_options = [
            selectinload(TWG.political_lead),
            selectinload(TWG.technical_lead),
        ]
        result = await db.execute(select(TWG).options(*query_options).limit(5))
        twgs = result.scalars().all()
        # Try accessing the nested relationship that might be causing lazy load error
        debug_data = []
        for t in twgs:
            p_lead_twgs = "N/A"
            if t.political_lead:
                # This access should crash if User.twgs is not loaded
                p_lead_twgs = str(len(t.political_lead.twgs))
            debug_data.append({"name": t.name, "pillar": str(t.pillar), "leads_twgs_loaded": p_lead_twgs})
            
        return {"status": "success", "count": len(twgs), "data": debug_data}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

@router.get("/debug/test_documents")
async def test_documents(db: AsyncSession = Depends(get_db)):
    """Runs the exact query from list_documents to capture the error."""
    try:
        from app.models.models import Document
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db.execute(select(Document).limit(5))
        docs = result.scalars().all()
        return {"status": "success", "count": len(docs)}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

@router.get("/debug/webhook_check")
async def webhook_check(db: AsyncSession = Depends(get_db)):
    """Check if webhook processing created transcript documents and updated meetings."""
    try:
        from app.models.models import Meeting, Document
        from sqlalchemy import select, or_

        # Find meetings with transcripts
        result = await db.execute(
            select(Meeting.id, Meeting.title, Meeting.status, Meeting.transcript).where(
                Meeting.transcript.isnot(None), Meeting.transcript != ""
            ).order_by(Meeting.updated_at.desc()).limit(5)
        )
        meetings_with_transcripts = [
            {"id": str(r[0]), "title": r[1], "status": str(r[2]), "transcript_len": len(r[3]) if r[3] else 0}
            for r in result.fetchall()
        ]

        # Find transcript documents
        doc_result = await db.execute(
            select(Document.id, Document.file_name, Document.document_type, Document.meeting_id).where(
                Document.document_type.in_(["transcript", "transcript_placeholder"])
            ).order_by(Document.created_at.desc()).limit(5)
        )
        transcript_docs = [
            {"id": str(r[0]), "file_name": r[1], "type": r[2], "meeting_id": str(r[3]) if r[3] else None}
            for r in doc_result.fetchall()
        ]

        # Find minutes documents
        min_result = await db.execute(
            select(Document.id, Document.file_name, Document.document_type, Document.meeting_id).where(
                Document.document_type == "minutes"
            ).order_by(Document.created_at.desc()).limit(5)
        )
        minutes_docs = [
            {"id": str(r[0]), "file_name": r[1], "type": r[2], "meeting_id": str(r[3]) if r[3] else None}
            for r in min_result.fetchall()
        ]

        return {
            "meetings_with_transcripts": meetings_with_transcripts,
            "transcript_documents": transcript_docs,
            "minutes_documents": minutes_docs,
        }
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

