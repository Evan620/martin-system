import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.continuous_monitor import ContinuousMonitor
from datetime import datetime, timezone
UTC = timezone.utc

@pytest.fixture
def monitor():
    return ContinuousMonitor()

@pytest.mark.asyncio
async def test_scan_scheduling_conflicts_no_conflicts(monitor):
    # Setup mock session
    session = AsyncMock()
    
    # Setup Context Manager mock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    
    # Patch WHERE IT IS USED
    with patch('app.services.continuous_monitor.get_db_session_context', return_value=cm) as mock_ctx:
        # Mock DB Query Result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [] # No meetings
        session.execute.return_value = mock_result
        
        await monitor.scan_scheduling_conflicts()
        
        assert session.execute.called

@pytest.mark.asyncio
async def test_scan_scheduling_conflicts_with_overlap(monitor):
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    
    with patch('app.services.continuous_monitor.get_db_session_context', return_value=cm):
        # Mock overlapping meetings
        m1 = MagicMock()
        m1.scheduled_at = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
        m1.duration_minutes = 120 # Ends at 12:00
        m1.venue = "Room A"
        m1.title = "Meeting 1"
        m1.twg_id = "twg1"
        
        m2 = MagicMock()
        m2.scheduled_at = datetime(2026, 3, 1, 11, 0, tzinfo=UTC) # Starts at 11:00 (Overlap)
        m2.duration_minutes = 120 # Ends at 13:00
        m2.venue = "Room A"
        m2.title = "Meeting 2"
        m2.twg_id = "twg2"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [m1, m2]
        session.execute.return_value = mock_result
        
        # Mock logger to verify warning
        with patch('app.services.continuous_monitor.logger') as mock_logger:
            await monitor.scan_scheduling_conflicts()
            assert mock_logger.warning.called
            assert "Conflict found: Venue conflict" in mock_logger.warning.call_args[0][0]

@pytest.mark.asyncio
async def test_scan_policy_divergences(monitor):
    session = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    
    with patch('app.services.continuous_monitor.get_db_session_context', return_value=cm):
        # Mock TWGs
        mock_twg = MagicMock()
        mock_twg.id = "twg1"
        mock_twg.name = "Energy"
        
        mock_twgs_result = MagicMock()
        mock_twgs_result.scalars.return_value.all.return_value = [mock_twg]
        
        # Mock Document
        mock_doc = MagicMock()
        mock_doc.file_name = "Policy.pdf"
        
        mock_doc_result = MagicMock()
        mock_doc_result.scalar_one_or_none.return_value = mock_doc
        
        # Configure execute side effects
        session.execute.side_effect = [mock_twgs_result, mock_doc_result]
        
        await monitor.scan_policy_divergences()
        
        assert session.execute.called

def test_monitor_lifecycle(monitor):
    with patch('app.services.continuous_monitor.AsyncIOScheduler') as mock_scheduler_cls:
        scheduler_instance = mock_scheduler_cls.return_value
        monitor.scheduler = scheduler_instance
        
        monitor.start()
        assert monitor.is_running
        assert scheduler_instance.start.called
        # Check jobs added (3 jobs)
        assert scheduler_instance.add_job.call_count == 3
        
        monitor.stop()
        assert not monitor.is_running
        assert scheduler_instance.shutdown.called
