from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import asyncio
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.models import User, UserRole
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/shared-documents", tags=["Shared Documents"])

@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_shared_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document to the Shared Documents folder in Google Drive.
    Only accessible by ADMIN and SECRETARIAT_LEAD roles.
    
    Returns:
        File metadata from Google Drive (id, name, webViewLink, etc.)
    """
    # Permission check: Only admins and secretariat leads can upload
    if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        raise HTTPException(
            status_code=403, 
            detail="Only administrators and secretariat leads can upload shared documents"
        )
    
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
        
        logger.info(f"User {current_user.email} uploaded shared document: {file.filename}")
        
        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded successfully",
            "file": result
        }
        
    except Exception as e:
        logger.error(f"Error uploading shared document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/", response_model=List[dict])
async def list_shared_documents(
    current_user: User = Depends(get_current_active_user)
):
    """
    List all files in the Shared Documents folder.
    Accessible by all authenticated users.
    
    Returns:
        List of file metadata from Google Drive
    """
    try:
        from app.services.drive_service import drive_service
        
        # Run blocking call in thread
        files = await asyncio.to_thread(drive_service.list_shared_documents)
        
        return files
        
    except Exception as e:
        logger.error(f"Error listing shared documents: {e}")
        # Return empty list gracefully instead of crashing UI
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
