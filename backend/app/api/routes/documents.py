from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
import os
import shutil
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.models.models import Document, User
from backend.app.schemas.schemas import DocumentRead
from backend.app.api.deps import get_current_active_user, has_twg_access
from backend.app.core.knowledge_base import get_knowledge_base
from backend.app.utils.document_processor import get_document_processor

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    twg_id: Optional[uuid.UUID] = Form(None),
    is_confidential: bool = Form(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document.
    """
    if twg_id and not has_twg_access(current_user, twg_id):
        raise HTTPException(status_code=403, detail="You do not have access to upload to this TWG")

    # Generate safe filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
        
    # Create DB record
    db_doc = Document(
        twg_id=twg_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file.content_type or "unknown",
        uploaded_by_id=current_user.id,
        is_confidential=is_confidential
    )
    
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)
    return db_doc

@router.get("/", response_model=List[DocumentRead])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    twg_id: uuid.UUID = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List documents.
    """
    query = select(Document).offset(skip).limit(limit)
    
    if twg_id:
        query = query.where(Document.twg_id == twg_id)
        if not has_twg_access(current_user, twg_id):
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        # Filter visible documents
        # For simplicity, if no TWG specified, return docs from user's TWGs or all if admin
        # (This logic can be refined)
        user_twg_ids = [twg.id for twg in current_user.twgs]
        query = query.where(Document.twg_id.in_(user_twg_ids))
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a document.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    db_doc = result.scalar_one_or_none()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if db_doc.twg_id and not has_twg_access(current_user, db_doc.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not os.path.exists(db_doc.file_path):
        raise HTTPException(status_code=404, detail="File on disk not found")
        
    return FileResponse(path=db_doc.file_path, filename=db_doc.file_name, media_type=db_doc.file_type)

@router.post("/{doc_id}/ingest", status_code=status.HTTP_200_OK)
async def ingest_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a document into the vector database (Pinecone).
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    db_doc = result.scalar_one_or_none()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not has_twg_access(current_user, db_doc.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    processor = get_document_processor()
    kb = get_knowledge_base()

    try:
        # Process document
        processed = processor.process_document(
            db_doc.file_path,
            additional_metadata={
                'twg_id': str(db_doc.twg_id),
                'doc_id': str(db_doc.id),
                'file_name': db_doc.file_name
            }
        )
        
        if processed['status'] != 'success':
            raise HTTPException(status_code=500, detail=f"Processing failed: {processed.get('error')}")

        # Prepare chunks for Pinecone
        documents = []
        for i, chunk in enumerate(processed['chunks']):
            documents.append({
                'id': f"{db_doc.id}_chunk_{i}",
                'text': chunk['text'],
                'metadata': chunk['metadata']
            })

        # Upsert to Pinecone
        namespace = f"twg-{str(db_doc.twg_id)}"
        upsert_result = kb.upsert_documents(documents=documents, namespace=namespace)

        return {
            "status": "success",
            "chunks_ingested": upsert_result['total_upserted'],
            "namespace": namespace
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@router.get("/search", response_model=List[dict])
async def search_documents_content(
    query: str,
    twg_id: Optional[uuid.UUID] = None,
    limit: int = 5,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search document content using vector similarity.
    """
    kb = get_knowledge_base()
    
    namespace = None
    if twg_id:
        if not has_twg_access(current_user, twg_id):
            raise HTTPException(status_code=403, detail="Access denied to this TWG")
        namespace = f"twg-{str(twg_id)}"

    # If no TWG specified, we could search across all user's TWGs
    # But for now, require twg_id or admin (simpler)
    if not twg_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="twg_id is required for non-admin search")

    results = kb.search(query=query, namespace=namespace, top_k=limit)
    return results
