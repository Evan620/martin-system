import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from app.models.models import User, UserRole, Conflict, ConflictStatus

@pytest.mark.asyncio
async def test_get_autonomous_conflict_log():
    # Setup
    with patch("app.api.routes.dashboard.get_db") as mock_get_db, \
         patch("app.api.routes.dashboard.get_current_active_user") as mock_get_user:
        
        # Mock DB
        mock_db = AsyncMock()
        mock_result = MagicMock()
        
        # Mock Conflicts
        c1 = MagicMock(spec=Conflict)
        c1.status = ConflictStatus.RESOLVED
        c1.resolution_log = [{"action": "auto_resolved"}]
        c1.detected_at = datetime.now(UTC)
        
        c2 = MagicMock(spec=Conflict)
        c2.status = ConflictStatus.ESCALATED
        c2.resolution_log = []
        c2.detected_at = datetime.now(UTC)
        
        mock_result.scalars.return_value.all.return_value = [c1, c2]
        mock_db.execute.return_value = mock_result
        
        # Mock User (Admin)
        admin_user = MagicMock(spec=User)
        admin_user.role = UserRole.ADMIN
        
        # Import the function to test
        # We need to import inside test or refactor app structure to be testable without running app
        # For simplicity, we'll assume we can import the router function if we mock dependencies
        from app.api.routes.dashboard import get_autonomous_conflict_log
        
        # Test Not Admin
        non_admin = MagicMock(spec=User)
        non_admin.role = UserRole.TWG_FACILITATOR
        with pytest.raises(Exception): # HTTPException
            await get_autonomous_conflict_log(7, mock_db, non_admin)
            
        # Test Success
        response = await get_autonomous_conflict_log(7, mock_db, admin_user)
        
        assert response["stats"]["total_detected"] == 2
        assert response["stats"]["auto_resolved"] == 1
        assert response["stats"]["escalated"] == 1
        assert response["stats"]["resolution_rate"] == 0.5
        assert len(response["conflicts"]) == 2
