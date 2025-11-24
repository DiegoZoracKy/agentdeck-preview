"""Console-level monitors for system observability.

Monitors observe console/system events (progress, workers, hardware metrics).
Distinct from Spectators which observe match narrative events.

Two-tier observation system:
- Spectators: Watch match events (buffered, replayed in order)
- Monitors: Watch console events (live, immediate)
"""

from .base import Monitor
from .progress import ProgressMonitor

__all__ = [
    "Monitor",
    "ProgressMonitor",
]
