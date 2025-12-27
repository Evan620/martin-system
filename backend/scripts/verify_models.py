import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

try:
    from app.models.models import Meeting, Minutes, Project, MinutesStatus, Document
    from app.schemas.schemas import MeetingRead, ProjectRead, MinutesStatus as SchemaMinutesStatus
    
    print("Successfully imported models and schemas.")
    
    # Verify fields
    assert hasattr(Meeting, "transcript"), "Meeting model missing transcript"
    assert hasattr(Minutes, "status"), "Minutes model missing status"
    assert hasattr(Project, "investment_memo_id"), "Project model missing investment_memo_id"
    
    # Verify Enums
    assert MinutesStatus.DRAFT == "draft"
    assert SchemaMinutesStatus.DRAFT == "draft"
    
    print("All checks passed.")
except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
