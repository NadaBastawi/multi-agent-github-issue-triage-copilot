"""
Debug tracing utilities for AgentForge.

Provides lightweight in-memory tracing used by the `agentforge logs` command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class TraceEvent:
    """Represents a single traced operation."""

    trace_id: str
    timestamp: datetime
    component: str
    function_name: str
    success: bool
    duration_ms: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class DebugTracer:
    """Simple in-memory tracer for operation timing and failure tracking."""

    def __init__(self, max_events: int = 5000):
        self.max_events = max_events
        self._events: List[TraceEvent] = []
        self._lock = Lock()

    def add_event(
        self,
        component: str,
        function_name: str,
        duration_ms: float = 0.0,
        success: bool = True,
        context: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> TraceEvent:
        """Add a trace event and enforce max history size."""
        event = TraceEvent(
            trace_id=f"TRACE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(),
            component=component,
            function_name=function_name,
            success=success,
            duration_ms=duration_ms,
            context=context or {},
            error_message=error_message,
        )

        with self._lock:
            self._events.append(event)
            if len(self._events) > self.max_events:
                self._events = self._events[-self.max_events :]

        return event

    def clear_traces(self):
        """Clear recorded trace history."""
        with self._lock:
            self._events.clear()

    def get_events(self) -> List[TraceEvent]:
        """Return a shallow copy of all trace events."""
        with self._lock:
            return list(self._events)

    def get_slow_operations(self, threshold_ms: float = 1000.0) -> List[TraceEvent]:
        """Return successful/failed events above the given duration threshold."""
        events = self.get_events()
        return sorted(
            [event for event in events if event.duration_ms >= threshold_ms],
            key=lambda event: event.duration_ms,
            reverse=True,
        )

    def get_failed_operations(self) -> List[TraceEvent]:
        """Return failed events sorted by newest first."""
        events = self.get_events()
        return sorted(
            [event for event in events if not event.success],
            key=lambda event: event.timestamp,
            reverse=True,
        )

    def get_performance_summary(self) -> Dict[str, Any]:
        """Return aggregate performance metrics for recorded events."""
        events = self.get_events()
        if not events:
            return {
                "total_events": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0.0,
                "total_duration_ms": 0.0,
            }

        total_events = len(events)
        success_count = sum(1 for event in events if event.success)
        total_duration = sum(event.duration_ms for event in events)

        return {
            "total_events": total_events,
            "success_rate": success_count / total_events,
            "average_duration_ms": total_duration / total_events,
            "total_duration_ms": total_duration,
        }


_tracer_instance: Optional[DebugTracer] = None


def get_tracer() -> DebugTracer:
    """Get shared tracer instance."""
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = DebugTracer()
    return _tracer_instance
