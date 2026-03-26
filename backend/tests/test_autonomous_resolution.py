import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.continuous_monitor import ContinuousMonitor
from app.models.models import ConflictStatus, ConflictType
from datetime import datetime, timezone
UTC = timezone.utc

@pytest.fixture
def monitor():
    return ContinuousMonitor()

@pytest.mark.asyncio
async def test_handle_detected_conflicts_triggers_negotiation(monitor):
    # Setup mocks
    session = AsyncMock()
    
    # Mock Conflict object creation - NOT patching Conflict class anymore to allow select()
    
    # Mock NegotiationService
    with patch('app.services.negotiation_service.NegotiationService') as MockNegotiationService:
        mock_reconciler = AsyncMock()
        MockNegotiationService.return_value = mock_reconciler
        
        # Mock negotiation result
        mock_reconciler.run_negotiation.return_value = {
            "status": "CONSENSUS_REACHED",
            "summary": "Resolved",
            "agreement_text": "Agreed to shift"
        }
        
        # Setup DB Mock for multiple calls
        # 1. Deduplication check (select Conflict) -> Return None (no duplicate)
        # 2. TWG Lookup (select TWG) -> Return Mock TWG
        
        # Result for Dedupe (Empty)
        mock_result_empty = MagicMock()
        mock_result_empty.scalars.return_value.first.return_value = None
        
        # Result for TWG (Found)
        mock_twg = MagicMock()
        mock_twg.technical_lead_id = "user-123"
        mock_twg.name = "Energy"
        mock_result_twg = MagicMock()
        mock_result_twg.scalar_one_or_none.return_value = mock_twg
        mock_result_twg.execute.return_value = mock_twg # fallback if needed
        
        # Configure side_effect
        session.execute.side_effect = [mock_result_empty, mock_result_twg, mock_result_twg]
        
        # Execute
        conflict_data = {
            "description": "Test Conflict",
            "conflict_type": "temporal",
            "severity": "high"
        }
        agents = ["twg1", "twg2"]
        
        await monitor._handle_detected_conflicts(session, conflict_data, agents)
        
        # Verify Conflict Creation
        # session.add might be called multiple times (Conflict + Notifications)
        assert session.add.called
        
        # Find the Conflict object among calls
        conflict_arg = None
        for call in session.add.call_args_list:
            arg = call[0][0]
            if hasattr(arg, 'description') and arg.description == "Test Conflict":
                conflict_arg = arg
                break
                
        assert conflict_arg is not None, "Conflict object was not added to session"
        
        # Verify Trigger
        assert MockNegotiationService.called
        assert mock_reconciler.run_negotiation.called
        mock_reconciler.run_negotiation.assert_called() 
        
        # Verify Commit
        assert session.commit.called

@pytest.mark.asyncio
async def test_scan_scheduling_conflicts_calls_handler(monitor):
    # Setup mocks similar to previous tests but checking for handler call
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    
    # Mock ConflictDetector
    with patch('app.services.continuous_monitor.ConflictDetector') as MockDetector:
        mock_detector_instance = MagicMock()
        MockDetector.return_value = mock_detector_instance
        
        # Make detector return one conflict
        mock_detector_instance.detect_scheduling_conflicts.return_value = [{
            "description": "Overlap M1 M2",
            "conflict_type": "temporal",
            "severity": "high",
            "conflicting_positions": {}
        }]

        with patch('app.services.continuous_monitor.get_db_session_context', return_value=cm):
            # Mock overlapping meetings
            m1 = MagicMock()
            m1.scheduled_at = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
            m1.duration_minutes = 120
            m1.location = "Room A" # Changed from venue to location
            m1.title = "M1"
            m1.twg_id = "twg1"
            
            m2 = MagicMock()
            m2.scheduled_at = datetime(2026, 3, 1, 11, 0, tzinfo=UTC)
            m2.duration_minutes = 120
            m2.location = "Room A" # Changed from venue to location
            m2.title = "M2"
            m2.twg_id = "twg2"
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [m1, m2]
            session.execute.return_value = mock_result
            
            # Mock _handle_detected_conflicts
            with patch.object(monitor, '_handle_detected_conflicts', new_callable=AsyncMock) as mock_handle:
                # Force using the mock detector
                monitor.detector = mock_detector_instance
                
                await monitor.scan_scheduling_conflicts()
                
                assert mock_handle.called
                # Verify arguments
                args = mock_handle.call_args
                # Check against Enum or string value if known. Assuming Enum.
                assert args.kwargs['conflict_data']['conflict_type'] == ConflictType.SCHEDULE_CLASH
                assert set(args.kwargs['agents_involved']) == {"twg1", "twg2"}
