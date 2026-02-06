from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.models import User, UserRole, Document
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/shared-documents", tags=["Shared Documents"])

@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_shared_document(
    file: UploadFile = File(...),
    access_control: Optional[str] = Form("all_twgs"),
    shared_with_twg_ids: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document to the Shared Documents folder in Google Drive.
    Only accessible by ADMIN and SECRETARIAT_LEAD roles.

    access_control: "all_twgs" (default, visible to everyone) or "specific_twgs"
    shared_with_twg_ids: comma-separated TWG UUIDs when access_control is "specific_twgs"

    Returns:
        File metadata from Google Drive (id, name, webViewLink, etc.)
    """
    # Permission check: Only admins and secretariat leads can upload
    if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and secretariat leads can upload shared documents"
        )

    # Parse access control
    if access_control not in ("all_twgs", "specific_twgs"):
        access_control = "all_twgs"

    parsed_scope = []
    if access_control == "specific_twgs" and shared_with_twg_ids:
        for tid in shared_with_twg_ids.split(","):
            tid = tid.strip()
            if tid:
                try:
                    uuid.UUID(tid)
                    parsed_scope.append(tid)
                except ValueError:
                    pass
        if not parsed_scope:
            access_control = "all_twgs"

    # Validate file size (50MB limit)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of 50MB"
        )

    # Validate file type (optional - can be expanded)
    allowed_types = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'application/vnd.google-apps.document',
        'application/vnd.google-apps.spreadsheet',
        'application/vnd.google-apps.presentation',
        'image/png',
        'image/jpeg',
        'text/plain'
    ]

    if file.content_type and file.content_type not in allowed_types:
        logger.warning(f"Uploading file with type: {file.content_type}")

    try:
        from app.services.drive_service import drive_service

        # Upload to Google Drive (run in thread since it's blocking)
        result = await asyncio.to_thread(
            drive_service.upload_file_to_drive,
            file_content,
            file.filename,
            file.content_type or 'application/octet-stream'
        )

        # Create a DB record to track sharing/access control for this Drive file
        safe_file_type = (file.content_type or "unknown")[:50]
        db_doc = Document(
            file_name=file.filename,
            file_path=f"drive://{result.get('id', '')}",
            file_type=safe_file_type,
            document_type="shared_workspace",
            uploaded_by_id=current_user.id,
            access_control=access_control,
            scope=parsed_scope if access_control == "specific_twgs" else [],
            metadata_json={
                "drive_file_id": result.get("id"),
                "web_view_link": result.get("webViewLink"),
            }
        )
        db.add(db_doc)
        await db.commit()

        logger.info(f"User {current_user.email} uploaded shared document: {file.filename} (access: {access_control})")

        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded successfully",
            "file": result,
            "access_control": access_control,
            "scope": parsed_scope
        }

    except Exception as e:
        logger.error(f"Error uploading shared document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/", response_model=List[dict])
async def list_shared_documents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List files in the Shared Documents folder.
    Admins see all files. Regular users only see files shared with their TWGs or all TWGs.

    Returns:
        List of file metadata from Google Drive, filtered by access control
    """
    try:
        from app.services.drive_service import drive_service

        # Get all Drive files
        files = await asyncio.to_thread(drive_service.list_shared_documents)

        # Admins/Secretariat see everything
        if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
            return files

        # For regular users, check DB access records to filter
        user_twg_ids = [twg.id for twg in current_user.twgs]

        # Get all shared_workspace document records
        sharing_conditions = [
            Document.access_control == "all_twgs",
        ]
        for tid in user_twg_ids:
            sharing_conditions.append(Document.scope.contains([str(tid)]))

        stmt = select(Document).where(
            Document.document_type == "shared_workspace",
            or_(*sharing_conditions)
        )
        result = await db.execute(stmt)
        allowed_docs = result.scalars().all()

        # Build set of allowed Drive file IDs
        allowed_drive_ids = set()
        for doc in allowed_docs:
            drive_id = (doc.metadata_json or {}).get("drive_file_id")
            if drive_id:
                allowed_drive_ids.add(drive_id)

        # Also include any Drive files that don't have a DB record yet (legacy files — show to all)
        tracked_drive_ids = set()
        all_stmt = select(Document.metadata_json).where(Document.document_type == "shared_workspace")
        all_result = await db.execute(all_stmt)
        for row in all_result.scalars().all():
            did = (row or {}).get("drive_file_id")
            if did:
                tracked_drive_ids.add(did)

        filtered = [
            f for f in files
            if f.get("id") in allowed_drive_ids or f.get("id") not in tracked_drive_ids
        ]

        return filtered

    except Exception as e:
        logger.error(f"Error listing shared documents: {e}")
        return []

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shared_document(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a file from the Shared Documents folder in Google Drive.
    Only accessible by ADMIN and SECRETARIAT_LEAD roles.
    
    Args:
        file_id: Google Drive file ID
    """
    # Permission check: Only admins and secretariat leads can delete
    if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and secretariat leads can delete shared documents"
        )
    
    try:
        from app.services.drive_service import drive_service
        
        # Delete from Google Drive (run in thread since it's blocking)
        success = await asyncio.to_thread(
            drive_service.delete_file_from_drive,
            file_id
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete file from Google Drive"
            )

        # Also delete the DB tracking record if it exists
        from sqlalchemy.dialects.postgresql import JSONB
        stmt = select(Document).where(
            Document.document_type == "shared_workspace",
            Document.file_path == f"drive://{file_id}"
        )
        result = await db.execute(stmt)
        db_doc = result.scalar_one_or_none()
        if db_doc:
            await db.delete(db_doc)
            await db.commit()

        logger.info(f"User {current_user.email} deleted shared document: {file_id}")

        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shared document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
