"""
Global Scheduling Service

Manages cross-TWG scheduling to prevent overlaps, ensure proper sequencing,
and coordinate VIP engagements across multiple TWGs.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of scheduled events"""
    TWG_MEETING = "twg_meeting"
    MINISTERIAL_PREP = "ministerial_prep"
    VIP_ENGAGEMENT = "vip_engagement"
    TECHNICAL_SESSION = "technical_session"
    DEAL_ROOM_SESSION = "deal_room_session"
    COORDINATION_MEETING = "coordination_meeting"
    DEADLINE = "deadline"


class EventPriority(str, Enum):
    """Event priority levels"""
    CRITICAL = "critical"  # Ministerial, VIP
    HIGH = "high"          # Multi-TWG coordination
    MEDIUM = "medium"      # Single TWG meetings
    LOW = "low"            # Optional sessions


class ScheduledEvent(BaseModel):
    """A scheduled event"""
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    priority: EventPriority
    title: str
    description: Optional[str] = None

    # Timing
    start_time: datetime
    end_time: datetime
    duration_minutes: int

    # Participants
    required_twgs: List[str] = Field(default_factory=list)
    optional_twgs: List[str] = Field(default_factory=list)
    vip_attendees: List[str] = Field(default_factory=list)

    # Dependencies
    requires_completion_of: List[UUID] = Field(
        default_factory=list,
        description="Events that must complete before this one"
    )
    enables: List[UUID] = Field(
        default_factory=list,
        description="Events enabled by this one"
    )

    # Status
    status: str = Field(default="scheduled")  # scheduled, in_progress, completed, cancelled
    created_by: str = Field(default="supervisor")

    # Metadata
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    agenda: Optional[str] = None
    deliverables: List[str] = Field(default_factory=list)


class ScheduleConflict(BaseModel):
    """A detected scheduling conflict"""
    conflict_id: UUID = Field(default_factory=uuid4)
    conflict_type: str  # overlap, dependency_violation, resource_conflict
    severity: str  # critical, high, medium, low

    # Involved events
    event_ids: List[UUID]
    event_titles: List[str]

    # Description
    description: str
    impact: str

    # Resolution
    suggested_resolution: Optional[str] = None
    requires_manual_resolution: bool = False


class GlobalScheduler:
    """Service for managing global scheduling across all TWGs"""

    def __init__(self):
        """Initialize global scheduler"""
        self._events: Dict[UUID, ScheduledEvent] = {}
        self._conflicts: List[ScheduleConflict] = []

        # TWG availability tracking
        self._twg_calendars: Dict[str, List[Tuple[datetime, datetime]]] = {}

        # VIP calendars (simplified)
        self._vip_calendars: Dict[str, List[Tuple[datetime, datetime]]] = {}

    def schedule_event(
        self,
        event_type: EventType,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        required_twgs: List[str],
        priority: EventPriority = EventPriority.MEDIUM,
        description: Optional[str] = None,
        optional_twgs: Optional[List[str]] = None,
        vip_attendees: Optional[List[str]] = None,
        requires_completion_of: Optional[List[UUID]] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a new event with conflict detection.

        Args:
            event_type: Type of event
            title: Event title
            start_time: Start time
            duration_minutes: Duration in minutes
            required_twgs: TWGs that must participate
            priority: Event priority
            description: Event description
            optional_twgs: Optional TWG participants
            vip_attendees: VIP attendees
            requires_completion_of: Events that must complete first
            location: Event location

        Returns:
            Dict with event details and any detected conflicts

        Example:
            >>> result = scheduler.schedule_event(
            ...     event_type=EventType.MINISTERIAL_PREP,
            ...     title="Pre-Summit Ministerial Coordination",
            ...     start_time=datetime(2026, 3, 15, 14, 0),
            ...     duration_minutes=180,
            ...     required_twgs=["energy", "agriculture", "minerals"],
            ...     priority=EventPriority.CRITICAL,
            ...     vip_attendees=["Minister of Energy", "Minister of Agriculture"]
            ... )
        """
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = ScheduledEvent(
            event_type=event_type,
            priority=priority,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            required_twgs=required_twgs,
            optional_twgs=optional_twgs or [],
            vip_attendees=vip_attendees or [],
            requires_completion_of=requires_completion_of or [],
            location=location
        )

        # Check for conflicts
        conflicts = self._detect_conflicts(event)

        if conflicts:
            logger.warning(
                f"⚠️  Scheduling conflict detected for '{title}': "
                f"{len(conflicts)} conflicts"
            )

            # If critical conflicts, suggest alternatives
            critical_conflicts = [
                c for c in conflicts
                if c.severity in ["critical", "high"]
            ]

            if critical_conflicts:
                alternative_times = self._suggest_alternative_times(
                    event,
                    conflicts
                )

                return {
                    "status": "conflict",
                    "event": event,
                    "conflicts": conflicts,
                    "alternative_times": alternative_times,
                    "message": f"Cannot schedule due to {len(critical_conflicts)} critical conflicts"
                }

        # No critical conflicts - schedule the event
        self._events[event.event_id] = event
        self._update_calendars(event)

        logger.info(
            f"✓ Scheduled: '{title}' on {start_time.strftime('%Y-%m-%d %H:%M')} "
            f"with {len(required_twgs)} required TWGs"
        )

        return {
            "status": "scheduled",
            "event": event,
            "conflicts": conflicts,  # May have minor conflicts
            "event_id": event.event_id
        }

    def _detect_conflicts(self, event: ScheduledEvent) -> List[ScheduleConflict]:
        """Detect conflicts for an event"""
        conflicts = []

        # 1. Check for time overlaps with required TWGs
        overlap_conflicts = self._check_time_overlaps(event)
        conflicts.extend(overlap_conflicts)

        # 2. Check dependency violations
        dependency_conflicts = self._check_dependencies(event)
        conflicts.extend(dependency_conflicts)

        # 3. Check VIP availability
        if event.vip_attendees:
            vip_conflicts = self._check_vip_availability(event)
            conflicts.extend(vip_conflicts)

        # 4. Check for resource conflicts (same location)
        if event.location:
            location_conflicts = self._check_location_conflicts(event)
            conflicts.extend(location_conflicts)

        return conflicts

    def _check_time_overlaps(self, new_event: ScheduledEvent) -> List[ScheduleConflict]:
        """Check if event overlaps with existing TWG commitments"""
        conflicts = []

        for existing_event in self._events.values():
            # Check if time ranges overlap
            if not self._times_overlap(
                new_event.start_time, new_event.end_time,
                existing_event.start_time, existing_event.end_time
            ):
                continue

            # Check if same TWGs involved
            common_twgs = set(new_event.required_twgs) & set(existing_event.required_twgs)

            if common_twgs:
                conflicts.append(ScheduleConflict(
                    conflict_type="overlap",
                    severity="high" if new_event.priority == EventPriority.CRITICAL else "medium",
                    event_ids=[new_event.event_id, existing_event.event_id],
                    event_titles=[new_event.title, existing_event.title],
                    description=f"TWGs {', '.join(common_twgs)} have overlapping commitments",
                    impact=f"Cannot attend both events simultaneously",
                    suggested_resolution=f"Reschedule one event or use different TWG representatives",
                    requires_manual_resolution=new_event.priority == EventPriority.CRITICAL
                ))

        return conflicts

    def _times_overlap(
        self,
        start1: datetime, end1: datetime,
        start2: datetime, end2: datetime
    ) -> bool:
        """Check if two time ranges overlap"""
        return start1 < end2 and end1 > start2

    def _check_dependencies(self, event: ScheduledEvent) -> List[ScheduleConflict]:
        """Check if dependency requirements are met"""
        conflicts = []

        for dep_id in event.requires_completion_of:
            if dep_id not in self._events:
                continue

            dep_event = self._events[dep_id]

            # Check if dependency completes before this event starts
            if dep_event.end_time >= event.start_time:
                conflicts.append(ScheduleConflict(
                    conflict_type="dependency_violation",
                    severity="high",
                    event_ids=[event.event_id, dep_id],
                    event_titles=[event.title, dep_event.title],
                    description=f"'{event.title}' starts before required event '{dep_event.title}' completes",
                    impact="Dependency event may not deliver required inputs in time",
                    suggested_resolution=f"Delay '{event.title}' to after {dep_event.end_time.strftime('%Y-%m-%d %H:%M')}",
                    requires_manual_resolution=True
                ))

        return conflicts

    def _check_vip_availability(self, event: ScheduledEvent) -> List[ScheduleConflict]:
        """Check VIP availability"""
        conflicts = []

        for vip in event.vip_attendees:
            vip_schedule = self._vip_calendars.get(vip, [])

            for busy_start, busy_end in vip_schedule:
                if self._times_overlap(
                    event.start_time, event.end_time,
                    busy_start, busy_end
                ):
                    conflicts.append(ScheduleConflict(
                        conflict_type="vip_conflict",
                        severity="critical",
                        event_ids=[event.event_id],
                        event_titles=[event.title],
                        description=f"VIP '{vip}' has another commitment at this time",
                        impact="VIP cannot attend",
                        suggested_resolution="Reschedule to accommodate VIP availability",
                        requires_manual_resolution=True
                    ))

        return conflicts

    def _check_location_conflicts(self, event: ScheduledEvent) -> List[ScheduleConflict]:
        """Check for location double-booking"""
        conflicts = []

        for existing_event in self._events.values():
            if existing_event.location == event.location:
                if self._times_overlap(
                    event.start_time, event.end_time,
                    existing_event.start_time, existing_event.end_time
                ):
                    conflicts.append(ScheduleConflict(
                        conflict_type="location_conflict",
                        severity="medium",
                        event_ids=[event.event_id, existing_event.event_id],
                        event_titles=[event.title, existing_event.title],
                        description=f"Location '{event.location}' double-booked",
                        impact="Venue not available",
                        suggested_resolution="Use different location or reschedule",
                        requires_manual_resolution=False
                    ))

        return conflicts

    def _suggest_alternative_times(
        self,
        event: ScheduledEvent,
        conflicts: List[ScheduleConflict]
    ) -> List[datetime]:
        """Suggest alternative times that avoid conflicts"""
        alternatives = []

        # Try next available slots
        search_start = event.start_time
        duration = timedelta(minutes=event.duration_minutes)

        for _ in range(10):  # Try 10 alternatives
            # Move forward by 1 hour
            search_start = search_start + timedelta(hours=1)

            # Create test event
            test_event = event.model_copy()
            test_event.start_time = search_start
            test_event.end_time = search_start + duration

            # Check if this time works
            test_conflicts = self._detect_conflicts(test_event)
            critical = [c for c in test_conflicts if c.severity in ["critical", "high"]]

            if not critical:
                alternatives.append(search_start)

                if len(alternatives) >= 3:
                    break

        return alternatives

    def _update_calendars(self, event: ScheduledEvent) -> None:
        """Update TWG and VIP calendars with event"""
        # Update TWG calendars
        for twg_id in event.required_twgs:
            if twg_id not in self._twg_calendars:
                self._twg_calendars[twg_id] = []

            self._twg_calendars[twg_id].append((event.start_time, event.end_time))

        # Update VIP calendars
        for vip in event.vip_attendees:
            if vip not in self._vip_calendars:
                self._vip_calendars[vip] = []

            self._vip_calendars[vip].append((event.start_time, event.end_time))

    def get_twg_schedule(
        self,
        twg_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ScheduledEvent]:
        """Get schedule for a specific TWG"""
        events = []

        for event in self._events.values():
            # Check if TWG is involved
            if twg_id not in event.required_twgs and twg_id not in event.optional_twgs:
                continue

            # Check date range
            if start_date and event.end_time < start_date:
                continue
            if end_date and event.start_time > end_date:
                continue

            events.append(event)

        # Sort by start time
        events.sort(key=lambda e: e.start_time)

        return events

    def get_global_schedule(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ScheduledEvent]:
        """Get global schedule across all TWGs"""
        events = list(self._events.values())

        # Filter by date range
        if start_date:
            events = [e for e in events if e.end_time >= start_date]
        if end_date:
            events = [e for e in events if e.start_time <= end_date]

        # Sort by start time
        events.sort(key=lambda e: e.start_time)

        return events

    def detect_all_conflicts(self) -> List[ScheduleConflict]:
        """Detect all conflicts in current schedule"""
        all_conflicts = []

        for event in self._events.values():
            conflicts = self._detect_conflicts(event)
            all_conflicts.extend(conflicts)

        # Deduplicate
        seen = set()
        unique_conflicts = []

        for conflict in all_conflicts:
            conflict_key = (
                conflict.conflict_type,
                tuple(sorted(conflict.event_ids))
            )

            if conflict_key not in seen:
                seen.add(conflict_key)
                unique_conflicts.append(conflict)

        return unique_conflicts

    def resolve_conflict(
        self,
        conflict_id: UUID,
        resolution: str,
        new_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Resolve a scheduling conflict"""
        # Find conflict
        conflict = None
        for c in self._conflicts:
            if c.conflict_id == conflict_id:
                conflict = c
                break

        if not conflict:
            return {"status": "error", "message": "Conflict not found"}

        # Apply resolution
        if resolution == "reschedule" and new_time:
            # Reschedule first event to new time
            event_id = conflict.event_ids[0]
            if event_id in self._events:
                event = self._events[event_id]
                duration = timedelta(minutes=event.duration_minutes)

                event.start_time = new_time
                event.end_time = new_time + duration

                logger.info(f"✓ Rescheduled '{event.title}' to {new_time}")

                return {
                    "status": "resolved",
                    "conflict_id": conflict_id,
                    "action": "rescheduled",
                    "new_time": new_time
                }

        return {"status": "pending", "message": "Manual resolution required"}

    def get_critical_path(
        self,
        target_event_id: UUID
    ) -> List[ScheduledEvent]:
        """
        Get critical path of events leading to a target event.

        This identifies the sequence of dependent events that must complete
        for the target event to proceed.
        """
        if target_event_id not in self._events:
            return []

        critical_path = []
        to_process = [target_event_id]
        processed = set()

        while to_process:
            current_id = to_process.pop(0)

            if current_id in processed:
                continue

            processed.add(current_id)
            current_event = self._events.get(current_id)

            if current_event:
                critical_path.append(current_event)

                # Add dependencies to process
                to_process.extend(current_event.requires_completion_of)

        # Reverse to get chronological order
        critical_path.reverse()

        return critical_path

    def get_scheduling_summary(self) -> Dict[str, Any]:
        """Get summary of current schedule"""
        total_events = len(self._events)
        by_type = {}
        by_priority = {}
        by_status = {}

        for event in self._events.values():
            # Count by type
            event_type = event.event_type.value
            by_type[event_type] = by_type.get(event_type, 0) + 1

            # Count by priority
            priority = event.priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Count by status
            status = event.status
            by_status[status] = by_status.get(status, 0) + 1

        conflicts = self.detect_all_conflicts()

        return {
            "total_events": total_events,
            "by_type": by_type,
            "by_priority": by_priority,
            "by_status": by_status,
            "total_conflicts": len(conflicts),
            "critical_conflicts": len([c for c in conflicts if c.severity == "critical"])
        }
