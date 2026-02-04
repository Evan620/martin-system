from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.models import Document, User, UserRole
from app.schemas.schemas import DocumentRead
from app.api.deps import get_current_active_user, has_twg_access
from app.core.knowledge_base import get_knowledge_base
from app.utils.document_processor import get_document_processor

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    twg_id: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    is_confidential: bool = Form(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document.
    
    twg_id can be either:
    - A UUID string (for backward compatibility)
    - A pillar key: energy, agriculture, minerals, digital, protocol, resource_mobilization
    - None/empty for Global Secretariat
    
    project_id: Optional UUID string to link document to a project
    document_type: Optional document type (feasibility_study, esia, financial_model, etc.)
    """
    resolved_twg_id = None
    resolved_project_id = None
    
    # Parse project_id if provided
    if project_id:
        try:
            resolved_project_id = uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid project_id: must be UUID")
    
    if twg_id:
        # Map pillar keys to enum values for lookup
        pillar_map = {
            "energy": "energy_infrastructure",
            "agriculture": "agriculture_food_systems",
            "minerals": "critical_minerals_industrialization",
            "digital": "digital_economy_transformation",
            "protocol": "protocol_logistics",
            "resource_mobilization": "resource_mobilization"
        }
        
        if twg_id == "global":
            resolved_twg_id = None
        else:
            # Try to parse as UUID first
            try:
                resolved_twg_id = uuid.UUID(twg_id)
            except ValueError:
                # Not a UUID, try to resolve as pillar key
                if twg_id in pillar_map:
                    from app.models.models import TWG
                    pillar_value = pillar_map[twg_id]
                    result = await db.execute(
                        select(TWG).where(TWG.pillar == pillar_value)
                    )
                    twg = result.scalar_one_or_none()
                    if twg:
                        resolved_twg_id = twg.id
                    else:
                        raise HTTPException(status_code=404, detail=f"TWG with pillar '{twg_id}' not found")
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid twg_id: must be UUID, 'global', or pillar key")
    
    if resolved_twg_id and not has_twg_access(current_user, resolved_twg_id):
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
    # Workaround: Explicitly truncate file_type to 50 chars to avoid persistent DBAPIError
    safe_file_type = (file.content_type or "unknown")[:50]
    
    # Build metadata_json with document_type if provided
    metadata = {}
    if document_type:
        metadata["document_type"] = document_type
    
    db_doc = Document(
        twg_id=resolved_twg_id,
        project_id=resolved_project_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=safe_file_type,
        uploaded_by_id=current_user.id,
        is_confidential=is_confidential,
        metadata_json=metadata if metadata else None
    )
    
    db.add(db_doc)
    await db.commit()
    
    # Reload with relationships instead of refresh
    result = await db.execute(
        select(Document)
        .where(Document.id == db_doc.id)
        .options(
            selectinload(Document.twg),
            selectinload(Document.uploaded_by)
        )
    )
    db_doc = result.scalar_one()
    
    # AUTOMATIC SCORING: If document is linked to a project, trigger AfCEN assessment
    if resolved_project_id:
        try:
            from app.services.scoring_tasks import rescore_project_async
            
            # Trigger background scoring via Celery (if available)
            rescore_project_async.delay(str(resolved_project_id))
            
            logger.info(f"✓ Triggered automatic AfCEN assessment for project {resolved_project_id}")
        except (ConnectionRefusedError, ConnectionError) as e:
            # Celery/Redis not available - log warning but don't crash
            logger.warning(f"⚠️ Celery unavailable, skipping background scoring: {e}")
            logger.info(f"💡 Tip: Manually trigger scoring via POST /api/v1/pipeline/{resolved_project_id}/rescore")
        except Exception as e:
            # Don't fail upload if scoring fails for any other reason
            logger.warning(f"Could not trigger automatic scoring: {e}")
    
    return db_doc

@router.get("/", response_model=List[DocumentRead])
async def list_documents(
    response: Response,
    skip: int = 0,
    limit: int = 100,
    twg_id: uuid.UUID = None,
    project_id: uuid.UUID = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List documents.
    """
    # Filtered documents for display: Eager load relationships
    # We need to import selectinload
    from sqlalchemy.orm import selectinload
    from sqlalchemy import func
    
    # Base query for counting (without eager loads)
    count_query = select(func.count(Document.id))
    
    # Query for fetching data
    query = select(Document).options(
        selectinload(Document.uploaded_by),
        selectinload(Document.twg)
    )
    
    try:
        if twg_id:
            count_query = count_query.where(Document.twg_id == twg_id)
            query = query.where(Document.twg_id == twg_id)
            if not has_twg_access(current_user, twg_id):
                raise HTTPException(status_code=403, detail="Access denied")
        elif project_id:
            # New project filter
            count_query = count_query.where(Document.project_id == project_id)
            query = query.where(Document.project_id == project_id)
            # Access control for project docs?
            # For now, if user has access to project's TWG, they see it.
            # But documents might not have TWG explicitly set if they are project-only?
            # Assuming project docs belong to the TWG of the project. 
            # We skip explicit check here relying on the fact that if they can see the project (RBAC elsewhere), they can see docs?
            # Or enforce generic RBAC.
            if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.TWG_FACILITATOR, UserRole.TWG_MEMBER]:
                 # Basic check
                 pass 
        else:
            # Filter visible documents based on user role and TWG membership
            if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
                # Admins and Secretariat Leads see all documents
                pass
            else:
                # STRICT RBAC: Regular users ONLY see:
                # 1. Documents from their assigned TWGs
                # 2. Global Secretariat documents (twg_id is NULL)
                # This enforces the "locked room" principle - no cross-TWG visibility
                user_twg_ids = [twg.id for twg in current_user.twgs]
                filter_condition = (Document.twg_id.in_(user_twg_ids)) | (Document.twg_id == None)
                
                count_query = count_query.where(filter_condition)
                query = query.where(filter_condition)
        
        # Execute count
        total_count = await db.scalar(count_query)
        
        # Apply pagination to data query and execute
        # Note: We must apply offset/limit AFTER filtering
        query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # Set header
        response.headers["X-Total-Count"] = str(total_count)
        
        return documents

    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in list_documents: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error listing documents")

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
        
    # Permission check
    if db_doc.twg_id and not has_twg_access(current_user, db_doc.twg_id):
        logger.warning(f"Access denied for user {current_user.email} (role: {current_user.role}) to doc {doc_id} (TWG: {db_doc.twg_id})")
        raise HTTPException(status_code=403, detail="Access denied")
        
    # Handle Transcript Placeholders specifically
    if db_doc.document_type == "transcript_placeholder":
        # Create a dynamic status file instead of looking for file on disk
        status_text = f" Transcript Processing Status\n" \
                      f"===========================\n\n" \
                      f"Meeting: {db_doc.file_name.replace('Vexa Recording - ', '')}\n" \
                      f"Status: Recording/Processing in progress\n" \
                      f"Session ID: {db_doc.metadata_json.get('vexa_session_id', 'Unknown')}\n\n" \
                      f"The audio is currently being transcribed. Once the meeting ends and processing is complete,\n" \
                      f"this file will be replaced with the final transcript and minutes will be generated.\n\n" \
                      f"Please come back later."
        
        return Response(content=status_text, media_type="text/plain", headers={
            "Content-Disposition": f"attachment; filename={db_doc.file_name or 'transcript_status.txt'}"
        })

    if not os.path.exists(db_doc.file_path):
        logger.error(f"File missing on disk: {db_doc.file_path} for doc {doc_id}")
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
        namespace = f"twg-{db_doc.twg_id}" if db_doc.twg_id else "twg-general"
        upsert_result = kb.upsert_documents(documents=documents, namespace=namespace)

        return {
            "status": "success",
            "chunks_ingested": upsert_result['total_upserted'],
            "namespace": namespace
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    # Update DB record with ingestion timestamp
    db_doc.ingested_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_doc)

    return {
        "status": "success",
        "chunks_ingested": upsert_result['total_upserted'],
        "namespace": namespace
    }

@router.get("/core-workspace", response_model=List[dict])
async def list_core_workspace_files(
    current_user: User = Depends(get_current_active_user)
):
    """
    List Google Docs/Sheets from the configured Core Workspace folder.
    Use this for the "Core Workspace" section in Documents.
    """
    try:
        from app.services.drive_service import drive_service
        
        # Run blocking call in thread
        import asyncio
        files = await asyncio.to_thread(drive_service.list_core_workspace_files)
        
        return files
    except Exception as e:
        logger.error(f"Error fetching Core Workspace files: {e}")
        # Return empty list gracefully instead of crashing UI
        return []

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
    if not twg_id and current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        raise HTTPException(status_code=400, detail="twg_id is required for non-admin/secretariat search")

    results = kb.search(query=query, namespace=namespace, top_k=limit)
    return results

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a document and its file.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    db_doc = result.scalar_one_or_none()
    
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Only admin or uploader can delete
    if current_user.role != UserRole.ADMIN and db_doc.uploaded_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    # Delete file from disk
    if os.path.exists(db_doc.file_path):
        try:
            os.remove(db_doc.file_path)
        except Exception as e:
            print(f"Error deleting file {db_doc.file_path}: {e}")

    # Store project_id before deletion
    project_id = db_doc.project_id

    # Delete from DB
    await db.delete(db_doc)
    await db.commit()
    
    # AUTOMATIC SCORING: If document was linked to a project, retrigger scoring
    if project_id:
        try:
            from app.services.scoring_tasks import rescore_project_async
            
            # Trigger background scoring via Celery (if available)
            rescore_project_async.delay(str(project_id))
            
            logger.info(f"✓ Triggered AfCEN rescoring for project {project_id} after document deletion")
        except (ConnectionRefusedError, ConnectionError) as e:
            # Celery/Redis not available - log warning but don't crash
            logger.warning(f"⚠️ Celery unavailable, skipping background scoring: {e}")
            logger.info(f"💡 Tip: Manually trigger scoring via POST /api/v1/pipeline/{project_id}/rescore")
        except Exception as e:
            logger.warning(f"Could not trigger automatic scoring: {e}")
    
    return None

@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_documents(
    doc_ids: List[uuid.UUID],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple documents.
    """
    if not doc_ids:
        return None

    # Get documents to delete
    result = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
    db_docs = result.scalars().all()
    
    for db_doc in db_docs:
        # Check permissions for each (unless admin)
        if current_user.role != UserRole.ADMIN and db_doc.uploaded_by_id != current_user.id:
            continue
            
        # Delete file from disk
        if os.path.exists(db_doc.file_path):
            try:
                os.remove(db_doc.file_path)
            except Exception as e:
                print(f"Error deleting file {db_doc.file_path}: {e}")

        # Delete from DB
        await db.delete(db_doc)
    
    await db.commit()
    return None
