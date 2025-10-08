"""
CPU information collector.

Detects CPU model, family, and configuration from /proc/cpuinfo.
"""

from typing import Dict, Any


class CPUInfoCollector:
    """
    Collect CPU configuration from /proc/cpuinfo.

    Detects AMD Zen architecture, core count, and frequency.
    """

    def get_system_info(self) -> Dict[str, Any]:
        """
        Collect CPU information.

        Returns:
            Dictionary containing:
            - cpu_model: CPU model name
            - cpu_family: CPU family number
            - cpu_model_num: CPU model number
            - cpu_cores: Number of CPU cores
            - cpu_threads: Number of threads (logical CPUs)
            - cpu_mhz: Current CPU frequency in MHz
            - is_zen5: Boolean indicating Zen 5 detection
        """
        info = {}
        cores = set()

        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        if "cpu_model" not in info:
                            info["cpu_model"] = line.split(":", 1)[1].strip()
                    elif line.startswith("cpu family"):
                        if "cpu_family" not in info:
                            info["cpu_family"] = int(line.split(":")[1].strip())
                    elif line.startswith("model"):
                        if "cpu_model_num" not in info:
                            # This is "model" not "model name"
                            parts = line.split(":", 1)
                            if len(parts) == 2 and parts[0].strip() == "model":
                                info["cpu_model_num"] = int(parts[1].strip())
                    elif line.startswith("core id"):
                        cores.add(int(line.split(":")[1].strip()))
                    elif line.startswith("cpu MHz"):
                        if "cpu_mhz" not in info:
                            info["cpu_mhz"] = float(line.split(":")[1].strip())
                    elif line.startswith("processor"):
                        # Count logical CPUs
                        info["cpu_threads"] = info.get("cpu_threads", 0) + 1

            if cores:
                info["cpu_cores"] = len(cores)

            # Detect Zen 5 (family 25, model 0x60+)
            if info.get("cpu_family") == 25 and info.get("cpu_model_num", 0) >= 0x60:
                info["is_zen5"] = True
            else:
                info["is_zen5"] = False

        except (FileNotFoundError, ValueError, IndexError):
            pass

        return {"cpu": info} if info else {}
