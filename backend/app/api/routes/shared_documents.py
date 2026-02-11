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

@router.post("/add-link", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_drive_link(
    drive_url: str = Form(...),
    access_control: Optional[str] = Form("all_twgs"),
    shared_with_twg_ids: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an existing Google Drive file/folder to the Shared Documents.

    IMPORTANT: The file must already be shared in Google Drive as "Anyone with the link can view/edit".
    This system only controls which TWGs see the link in the Core Workspace UI.

    Accessible by ADMIN, SECRETARIAT_LEAD, TWG_FACILITATOR, and TWG leads.
    - Admins/Secretariat can share to any TWGs or all TWGs
    - TWG facilitators and leads can only share to their assigned TWGs

    drive_url: Full Google Drive URL (supports docs, sheets, slides, folders)
    access_control: "all_twgs" (default) or "specific_twgs"
    shared_with_twg_ids: comma-separated TWG UUIDs when access_control is "specific_twgs"

    Returns:
        File metadata from Google Drive
    """
    # Check if user is TWG lead and get their TWG
    user_twg_ids = []
    is_twg_lead = False
    is_facilitator = current_user.role == UserRole.TWG_FACILITATOR

    if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        # Admins and Secretariat can share to any TWG - access_control is respected
        pass
    else:
        # For TWG facilitators and leads, get their assigned TWGs
        from app.models.models import TWG
        from sqlalchemy.orm import selectinload

        if is_facilitator:
            # Facilitators use their assigned twg_ids
            # Load user with their TWGs
            await db.refresh(current_user, attribute_names=['twgs'])
            user_twg_ids = [str(twg.id) for twg in current_user.twgs]

            if not user_twg_ids:
                raise HTTPException(
                    status_code=403,
                    detail="TWG facilitators must be assigned to at least one TWG to share documents"
                )
        else:
            # For TWG leads (political/technical), find which TWGs they lead
            twg_result = await db.execute(
                select(TWG).where(
                    (TWG.political_lead_id == current_user.id) | (TWG.technical_lead_id == current_user.id)
                )
            )
            led_twgs = twg_result.scalars().all()

            if not led_twgs:
                raise HTTPException(
                    status_code=403,
                    detail="TWG leads must be assigned as a political or technical lead of at least one TWG to share documents"
                )

            is_twg_lead = True
            user_twg_ids = [str(twg.id) for twg in led_twgs]

        # Facilitators and TWG leads can only share to their assigned TWGs - force specific_twgs access
        access_control = "specific_twgs"
        if shared_with_twg_ids:
            # Filter to only include TWGs they're actually assigned to
            requested_ids = [tid.strip() for tid in shared_with_twg_ids.split(",") if tid.strip()]
            valid_ids = [tid for tid in requested_ids if tid in user_twg_ids]
            shared_with_twg_ids = ",".join(valid_ids) if valid_ids else user_twg_ids[0]
        else:
            # Default to their first TWG if none specified
            shared_with_twg_ids = user_twg_ids[0]

    # Parse access control (for admins/secretariat only)
    if not is_twg_lead and not is_facilitator and access_control not in ("all_twgs", "specific_twgs"):
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

    try:
        from app.services.drive_service import drive_service
        from app.models.models import TWG
        from sqlalchemy.orm import selectinload

        # Extract file ID from URL
        file_id = await asyncio.to_thread(drive_service.extract_file_id_from_url, drive_url)
        if not file_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid Google Drive URL. Could not extract file ID."
            )

        # Get file metadata to verify it exists
        file_metadata = await asyncio.to_thread(drive_service.get_file_metadata, file_id)
        if not file_metadata:
            raise HTTPException(
                status_code=404,
                detail="File not found or you don't have access to it."
            )

        # Create a shortcut in the shared folder
        await asyncio.to_thread(drive_service.add_file_to_shared_folder, file_id)

        # Create a DB record to track which TWGs can see this link
        safe_file_type = (file_metadata.get('mimeType', "unknown")[:50])
        db_doc = Document(
            file_name=file_metadata.get('name', 'Unnamed File'),
            file_path=f"drive://{file_id}",
            file_type=safe_file_type,
            document_type="shared_workspace",
            uploaded_by_id=current_user.id,
            access_control=access_control,
            scope=parsed_scope if access_control == "specific_twgs" else [],
            metadata_json={
                "drive_file_id": file_id,
                "web_view_link": file_metadata.get("webViewLink"),
                "is_link": True
            }
        )
        db.add(db_doc)
        await db.commit()

        logger.info(f"User {current_user.email} added Drive link: {file_metadata.get('name')} (access: {access_control})")

        return {
            "status": "success",
            "message": f"File '{file_metadata.get('name')}' added successfully",
            "file": file_metadata,
            "access_control": access_control,
            "scope": parsed_scope
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding Drive link: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add file link: {str(e)}"
        )

@router.post("/set-permissions", response_model=dict, status_code=status.HTTP_200_OK)
async def set_drive_file_permissions(
    file_id: str = Form(...),
    emails: str = Form(...),  # Comma-separated email addresses
    permission_role: str = Form("viewer"),  # viewer, commenter, writer
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set permissions on a Google Drive file for specific users.
    Only accessible by ADMIN and SECRETARIAT_LEAD roles.

    file_id: Google Drive file ID
    emails: Comma-separated list of email addresses
    permission_role: "viewer", "commenter", or "writer"

    Returns:
        Success status
    """
    # Permission check: Only admins and secretariat leads can set permissions
    if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and secretariat leads can set permissions"
        )

    # Validate permission role
    role_map = {
        "viewer": "reader",
        "commenter": "commenter",
        "writer": "writer"
    }
    drive_role = role_map.get(permission_role, "reader")

    if permission_role not in role_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission role. Must be one of: {', '.join(role_map.keys())}"
        )

    # Parse emails
    email_list = [e.strip() for e in emails.split(",") if e.strip()]
    if not email_list:
        raise HTTPException(
            status_code=400,
            detail="At least one email address is required"
        )

    try:
        from app.services.drive_service import drive_service

        # Build permissions list
        permissions = [
            {
                "role": drive_role,
                "type": "user",
                "emailAddress": email
            }
            for email in email_list
        ]

        # Set permissions
        success = await asyncio.to_thread(
            drive_service.set_file_permissions,
            file_id,
            permissions
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to set permissions on Google Drive file"
            )

        logger.info(f"User {current_user.email} set {permission_role} permissions for {len(email_list)} users on file {file_id}")

        return {
            "status": "success",
            "message": f"Successfully set {permission_role} permissions for {len(email_list)} users",
            "file_id": file_id,
            "permission_role": permission_role,
            "email_count": len(email_list)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting permissions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set permissions: {str(e)}"
        )

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

    Accessible by ADMIN, SECRETARIAT_LEAD, TWG_FACILITATOR, and TWG leads.
    - Admins/Secretariat can share to any TWGs or all TWGs
    - TWG facilitators and leads can only share to their assigned TWGs

    access_control: "all_twgs" (default, visible to everyone) or "specific_twgs"
    shared_with_twg_ids: comma-separated TWG UUIDs when access_control is "specific_twgs"

    Returns:
        File metadata from Google Drive (id, name, webViewLink, etc.)
    """
    # Check if user is TWG lead and get their TWG
    user_twg_ids = []
    is_twg_lead = False
    is_facilitator = current_user.role == UserRole.TWG_FACILITATOR

    if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        # Admins and Secretariat can share to any TWG - access_control is respected
        pass
    else:
        # For TWG facilitators and leads, get their assigned TWGs
        from app.models.models import TWG
        from sqlalchemy.orm import selectinload

        if is_facilitator:
            # Facilitators use their assigned twg_ids
            # Load user with their TWGs
            await db.refresh(current_user, attribute_names=['twgs'])
            user_twg_ids = [str(twg.id) for twg in current_user.twgs]

            if not user_twg_ids:
                raise HTTPException(
                    status_code=403,
                    detail="TWG facilitators must be assigned to at least one TWG to share documents"
                )
        else:
            # For TWG leads (political/technical), find which TWGs they lead
            twg_result = await db.execute(
                select(TWG).where(
                    (TWG.political_lead_id == current_user.id) | (TWG.technical_lead_id == current_user.id)
                )
            )
            led_twgs = twg_result.scalars().all()

            if not led_twgs:
                raise HTTPException(
                    status_code=403,
                    detail="TWG leads must be assigned as a political or technical lead of at least one TWG to share documents"
                )

            is_twg_lead = True
            user_twg_ids = [str(twg.id) for twg in led_twgs]

        # Facilitators and TWG leads can only share to their assigned TWGs - force specific_twgs access
        access_control = "specific_twgs"
        if shared_with_twg_ids:
            # Filter to only include TWGs they're actually assigned to
            requested_ids = [tid.strip() for tid in shared_with_twg_ids.split(",") if tid.strip()]
            valid_ids = [tid for tid in requested_ids if tid in user_twg_ids]
            shared_with_twg_ids = ",".join(valid_ids) if valid_ids else user_twg_ids[0]
        else:
            # Default to their first TWG if none specified
            shared_with_twg_ids = user_twg_ids[0]

    # Parse access control (for admins/secretariat only)
    if not is_twg_lead and not is_facilitator and access_control not in ("all_twgs", "specific_twgs"):
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
        from app.models.models import TWG
        from sqlalchemy.orm import selectinload

        # Upload to Google Drive (run in thread since it's blocking)
        result = await asyncio.to_thread(
            drive_service.upload_file_to_drive,
            file_content,
            file.filename,
            file.content_type or 'application/octet-stream'
        )

        # Collect emails of all users who should get access
        # For uploaded files, default to "writer" permission so they can collaborate
        emails_to_share = set()
        twgs_to_share = []
        drive_role = "writer"  # Uploaded files default to editor access

        if access_control == "all_twgs":
            # Get all active TWGs
            twg_result = await db.execute(
                select(TWG).where(TWG.status == "active")
                    .options(
                        selectinload(TWG.members),
                        selectinload(TWG.political_lead),
                        selectinload(TWG.technical_lead)
                    )
            )
            twgs_to_share = twg_result.scalars().all()
        else:
            # Get specific TWGs
            twg_result = await db.execute(
                select(TWG).where(TWG.id.in_(parsed_scope))
                    .options(
                        selectinload(TWG.members),
                        selectinload(TWG.political_lead),
                        selectinload(TWG.technical_lead)
                    )
            )
            twgs_to_share = twg_result.scalars().all()

        # Collect emails from TWG members and leads
        for twg in twgs_to_share:
            # Add all members
            for member in twg.members:
                if member.email and member.is_active:
                    emails_to_share.add(member.email)

            # Add political lead
            if twg.political_lead and twg.political_lead.email and twg.political_lead.is_active:
                emails_to_share.add(twg.political_lead.email)

            # Add technical lead
            if twg.technical_lead and twg.technical_lead.email and twg.technical_lead.is_active:
                emails_to_share.add(twg.technical_lead.email)

        # Share the file with all collected emails via Google Drive API
        shared_emails = []
        file_id = result.get('id', '')
        if emails_to_share and file_id:
            permissions = [
                {
                    "role": drive_role,
                    "type": "user",
                    "emailAddress": email
                }
                for email in emails_to_share
            ]

            share_success = await asyncio.to_thread(
                drive_service.set_file_permissions,
                file_id,
                permissions
            )

            if share_success:
                shared_emails = list(emails_to_share)
                logger.info(f"Successfully shared uploaded Drive file {file_id} with {len(shared_emails)} users as {drive_role}")

        # Create a DB record to track sharing/access control for this Drive file
        safe_file_type = (file.content_type or "unknown")[:50]
        db_doc = Document(
            file_name=file.filename,
            file_path=f"drive://{file_id}",
            file_type=safe_file_type,
            document_type="shared_workspace",
            uploaded_by_id=current_user.id,
            access_control=access_control,
            scope=parsed_scope if access_control == "specific_twgs" else [],
            metadata_json={
                "drive_file_id": file_id,
                "web_view_link": result.get("webViewLink"),
                "permission_level": "writer",  # Uploaded files default to writer
                "shared_with": shared_emails  # Track who we shared with
            }
        )
        db.add(db_doc)
        await db.commit()

        logger.info(f"User {current_user.email} uploaded shared document: {file.filename} (access: {access_control}, shared with: {len(shared_emails)} users)")

        return {
            "status": "success",
            "message": f"File '{file.filename}' uploaded successfully and shared with {len(shared_emails)} TWG members",
            "file": result,
            "access_control": access_control,
            "scope": parsed_scope,
            "shared_with_count": len(shared_emails)
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
        List of file metadata from Google Drive, with access_control and scope info
    """
    try:
        from app.services.drive_service import drive_service

        # Get all Drive files
        files = await asyncio.to_thread(drive_service.list_shared_documents)

        # Get all shared_workspace document records for access info
        stmt = select(Document).where(Document.document_type == "shared_workspace")
        result = await db.execute(stmt)
        all_shared_docs = result.scalars().all()

        # Build a map of drive_file_id -> access info
        access_info_map = {}
        for doc in all_shared_docs:
            drive_id = (doc.metadata_json or {}).get("drive_file_id")
            if drive_id:
                access_info_map[drive_id] = {
                    "access_control": doc.access_control or "all_twgs",
                    "scope": doc.scope or []
                }

        # Admins/Secretariat see everything with access info
        if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
            # Enrich files with access info
            return [
                {**f, "access_control": access_info_map.get(f.get("id"), {}).get("access_control", "all_twgs"),
                 "scope": access_info_map.get(f.get("id"), {}).get("scope", [])}
                for f in files
            ]

        # For regular users, check DB access records to filter
        user_twg_ids = [str(twg.id) for twg in current_user.twgs]

        logger.info(f"User {current_user.email} (TWGs: {user_twg_ids}) accessing shared documents")

        # Filter in Python to handle JSON scope properly
        allowed_drive_ids = set()
        for doc in all_shared_docs:
            # Admin documents (all_twgs access)
            if doc.access_control == "all_twgs":
                drive_id = (doc.metadata_json or {}).get("drive_file_id")
                if drive_id:
                    allowed_drive_ids.add(drive_id)
                    logger.debug(f"  → Allowing doc '{doc.file_name}' (access_control: all_twgs)")
                continue

            # Check specific TWG access
            doc_scope = doc.scope or []
            for user_tid in user_twg_ids:
                if user_tid in doc_scope:
                    drive_id = (doc.metadata_json or {}).get("drive_file_id")
                    if drive_id:
                        allowed_drive_ids.add(drive_id)
                        logger.debug(f"  → Allowing doc '{doc.file_name}' (user TWG {user_tid} in scope {doc_scope})")
                    break

        logger.info(f"User {current_user.email} can access {len(allowed_drive_ids)} shared documents")

        # Filter Drive files to only show allowed ones, with access info
        filtered = [
            {**f, "access_control": access_info_map.get(f.get("id"), {}).get("access_control", "all_twgs"),
             "scope": access_info_map.get(f.get("id"), {}).get("scope", [])}
            for f in files
            if f.get("id") in allowed_drive_ids
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
    Handles both regular files and shortcuts.
    Only accessible by ADMIN and SECRETARIAT_LEAD roles.

    Args:
        file_id: Google Drive file ID (can be target file ID for shortcuts)
    """
    # Permission check: Only admins and secretariat leads can delete
    if current_user.role not in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators and secretariat leads can delete shared documents"
        )

    try:
        from app.services.drive_service import drive_service

        # First, find the DB record to check if this is a shortcut or uploaded file
        # Search by drive_file_id in metadata_json (since that's what we store)
        stmt = select(Document).where(
            Document.document_type == "shared_workspace"
        )
        result = await db.execute(stmt)
        all_docs = result.scalars().all()

        # Find the matching document (either by drive_file_id in metadata or by file_path)
        matching_doc = None
        shortcut_id_to_delete = None

        for doc in all_docs:
            metadata = doc.metadata_json or {}
            # Check if this document's drive_file_id matches
            if metadata.get("drive_file_id") == file_id:
                matching_doc = doc
                # For shortcuts, we need to find the actual shortcut ID to delete
                if metadata.get("is_link"):
                    # Search for the shortcut in the shared folder
                    shortcut_id = await asyncio.to_thread(
                        drive_service.find_shortcut_to_file,
                        file_id
                    )
                    if shortcut_id:
                        shortcut_id_to_delete = shortcut_id
                break
            # Also check file_path as fallback
            elif doc.file_path == f"drive://{file_id}":
                matching_doc = doc
                break

        if not matching_doc:
            raise HTTPException(
                status_code=404,
                detail="Document not found in database"
            )

        # Delete the shortcut (for links) or file (for uploads)
        id_to_delete = shortcut_id_to_delete if shortcut_id_to_delete else file_id

        success = await asyncio.to_thread(
            drive_service.delete_file_from_drive,
            id_to_delete
        )

        if not success:
            logger.warning(f"Failed to delete from Drive, but removing DB record: {id_to_delete}")

        # Delete the DB tracking record
        await db.delete(matching_doc)
        await db.commit()

        logger.info(f"User {current_user.email} deleted shared document: {file_id} (deleted Drive ID: {id_to_delete})")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shared document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
