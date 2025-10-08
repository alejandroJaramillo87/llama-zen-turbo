"""
Vmstat collector for page fault tracking.

Monitors /proc/vmstat deltas during benchmark execution.
"""

from typing import Dict, Any, Optional


class VmstatCollector:
    """
    Track page fault statistics from /proc/vmstat.

    Captures before/after snapshots to calculate deltas during benchmark.
    """

    def __init__(self):
        """Initialize collector with no baseline."""
        self.start_stats: Optional[Dict[str, int]] = None

    def _snapshot(self) -> Dict[str, int]:
        """
        Take a snapshot of /proc/vmstat.

        Returns:
            Dictionary of vmstat counters
        """
        stats = {}
        try:
            with open('/proc/vmstat') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) == 2:
                        key, value = parts
                        try:
                            stats[key] = int(value)
                        except ValueError:
                            pass
        except FileNotFoundError:
            pass
        return stats

    def start(self):
        """
        Capture baseline vmstat snapshot.

        Called before benchmark execution begins.
        """
        self.start_stats = self._snapshot()

    def stop(self) -> Dict[str, Any]:
        """
        Calculate vmstat deltas since start.

        Returns:
            Dictionary containing:
            - vmstat: Dictionary of delta values for key metrics
              - pgfault_delta: Total page faults
              - pgmajfault_delta: Major page faults (disk I/O)
              - thp_fault_alloc_delta: Transparent hugepage allocations
              - thp_fault_fallback_delta: THP allocation fallbacks
        """
        if self.start_stats is None:
            return {}

        end_stats = self._snapshot()
        deltas = {}

        # Track key metrics for hugepage analysis
        metrics = [
            'pgfault',           # Total page faults
            'pgmajfault',        # Major faults (disk I/O required)
            'thp_fault_alloc',   # Transparent hugepage allocations
            'thp_fault_fallback' # THP allocation fallbacks
        ]

        for key in metrics:
            if key in self.start_stats and key in end_stats:
                delta = end_stats[key] - self.start_stats[key]
                deltas[f"{key}_delta"] = delta

        return {"vmstat": deltas} if deltas else {}
