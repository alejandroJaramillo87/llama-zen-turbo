"""
Hugepage status collector.

Reads hugepage configuration from /proc/meminfo.
"""

from typing import Dict, Any


class HugepageCollector:
    """
    Collect hugepage status from /proc/meminfo.

    Tracks total, free, and size of hugepages configured on the system.
    """

    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect hugepage configuration.

        Returns:
            Dictionary containing:
            - hugepages_total: Total huge pages configured
            - hugepages_free: Available huge pages
            - hugepage_size_kb: Huge page size in KB
            - hugepages_used: Calculated used pages
            - hugepages_used_gb: Used hugepages in GB
        """
        info = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("HugePages_Total:"):
                        info["hugepages_total"] = int(line.split()[1])
                    elif line.startswith("HugePages_Free:"):
                        info["hugepages_free"] = int(line.split()[1])
                    elif line.startswith("Hugepagesize:"):
                        info["hugepage_size_kb"] = int(line.split()[1])

            # Calculate usage
            if "hugepages_total" in info and "hugepages_free" in info:
                info["hugepages_used"] = info["hugepages_total"] - info["hugepages_free"]

            if "hugepages_used" in info and "hugepage_size_kb" in info:
                used_kb = info["hugepages_used"] * info["hugepage_size_kb"]
                info["hugepages_used_gb"] = round(used_kb / (1024 * 1024), 2)

        except (FileNotFoundError, ValueError, IndexError):
            pass

        return {"hugepages": info} if info else {}
