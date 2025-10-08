"""
Perf stat collector for TLB and cache metrics.

Uses Linux perf to collect hardware performance counters.
"""

import subprocess
import re
from typing import Dict, Any, Optional


class PerfCollector:
    """
    Collect TLB and cache metrics via perf stat.

    Attaches to llama-server process and monitors:
    - TLB miss rates (dTLB, iTLB)
    - Cache miss rates
    - Instructions per cycle
    """

    def __init__(self, container_name: str = "llama-zen5"):
        """
        Initialize perf collector.

        Args:
            container_name: Docker container name to monitor
        """
        self.container_name = container_name
        self.pid: Optional[int] = None
        self.perf_process: Optional[subprocess.Popen] = None
        self.output_file = "/tmp/perf_output.txt"

    def _find_llama_pid(self) -> Optional[int]:
        """
        Find llama-server PID in Docker container.

        Returns:
            Process ID or None if not found
        """
        try:
            # Get process list from container
            result = subprocess.run(
                ["docker", "top", self.container_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse output to find llama-server
                for line in result.stdout.split('\n'):
                    if 'llama-server' in line or './server' in line:
                        # PID is typically the second column
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                return int(parts[1])
                            except ValueError:
                                pass
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None

    def start(self):
        """
        Start perf stat monitoring.

        Finds llama-server PID and starts background perf collection.
        """
        # Find target process
        self.pid = self._find_llama_pid()
        if self.pid is None:
            print(f"  Perf: WARN (could not find llama-server PID)")
            return

        # Define events to monitor
        # Start with basic events that work on most systems
        events = [
            'cycles',
            'instructions',
            'cache-misses',
            'cache-references',
            'dTLB-load-misses',
            'dTLB-loads',
        ]

        # Try to add iTLB events (may not be available on all systems)
        try:
            test_result = subprocess.run(
                ['perf', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'iTLB-load-misses' in test_result.stdout:
                events.extend(['iTLB-load-misses', 'iTLB-loads'])
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Start perf stat in background
        try:
            self.perf_process = subprocess.Popen(
                [
                    'perf', 'stat',
                    '-p', str(self.pid),
                    '-e', ','.join(events),
                    '-o', self.output_file
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"  Perf: OK (monitoring PID {self.pid})")
        except (FileNotFoundError, PermissionError) as e:
            print(f"  Perf: WARN (failed to start: {e})")
            self.perf_process = None

    def stop(self) -> Dict[str, Any]:
        """
        Stop perf monitoring and collect results.

        Returns:
            Dictionary containing:
            - perf: Dictionary of performance metrics
              - cycles, instructions, ipc
              - dTLB_miss_rate, iTLB_miss_rate
              - cache_miss_rate
        """
        if self.perf_process is None:
            return {}

        # Stop perf process
        try:
            self.perf_process.terminate()
            self.perf_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.perf_process.kill()
            self.perf_process.wait()

        # Parse perf output
        metrics = self._parse_perf_output()

        if metrics:
            print(f"  Perf: OK (collected {len(metrics)} metrics)")
            return {"perf": metrics}
        else:
            print(f"  Perf: WARN (no metrics collected)")
            return {}

    def _parse_perf_output(self) -> Dict[str, Any]:
        """
        Parse perf stat output file.

        Returns:
            Dictionary of parsed metrics
        """
        metrics = {}

        try:
            with open(self.output_file, 'r') as f:
                content = f.read()

            # Perf output format: "     123,456,789      event_name"
            # Pattern matches number with optional commas and event name
            pattern = r'\s*([\d,]+)\s+(\S+)'

            for line in content.split('\n'):
                match = re.search(pattern, line)
                if match:
                    value_str = match.group(1).replace(',', '')
                    event_name = match.group(2)

                    try:
                        value = int(value_str)
                        metrics[event_name] = value
                    except ValueError:
                        pass

            # Calculate derived metrics
            if 'cycles' in metrics and 'instructions' in metrics and metrics['cycles'] > 0:
                metrics['ipc'] = round(metrics['instructions'] / metrics['cycles'], 2)

            if 'dTLB-load-misses' in metrics and 'dTLB-loads' in metrics and metrics['dTLB-loads'] > 0:
                rate = (metrics['dTLB-load-misses'] / metrics['dTLB-loads']) * 100
                metrics['dTLB_miss_rate'] = round(rate, 3)

            if 'iTLB-load-misses' in metrics and 'iTLB-loads' in metrics and metrics['iTLB-loads'] > 0:
                rate = (metrics['iTLB-load-misses'] / metrics['iTLB-loads']) * 100
                metrics['iTLB_miss_rate'] = round(rate, 3)

            if 'cache-misses' in metrics and 'cache-references' in metrics and metrics['cache-references'] > 0:
                rate = (metrics['cache-misses'] / metrics['cache-references']) * 100
                metrics['cache_miss_rate'] = round(rate, 2)

        except FileNotFoundError:
            pass

        return metrics
