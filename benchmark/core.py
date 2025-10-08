"""
Core benchmark functionality for llama.cpp API testing.

Provides API client, test prompts, and orchestration logic.
"""

import statistics
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests

from .constants import STATUS_OK, STATUS_WARN, STATUS_ERROR


# Test prompts designed to stress different optimization aspects
BENCHMARK_PROMPTS = {
    "memory_sequential": {
        "description": "Sequential memory access pattern",
        "prompt": "Count from 1 to 20, writing each number on a new line:",
        "max_tokens": 100,
        "expected_pattern": "numbers"
    },
    "cache_loops": {
        "description": "CPU cache efficiency with repetitive patterns",
        "prompt": "Write the word 'test' exactly 15 times separated by spaces:",
        "max_tokens": 80,
        "expected_pattern": "repetition"
    },
    "compute_arithmetic": {
        "description": "Basic compute operations",
        "prompt": "Calculate: 2+2=, 5+5=, 10+10=, 20+20=, 50+50=",
        "max_tokens": 50,
        "expected_pattern": "calculations"
    },
    "memory_structured": {
        "description": "Structured data generation for memory allocation",
        "prompt": "Create a JSON object with three fields: name (string), age (number), active (boolean). Use simple values:",
        "max_tokens": 100,
        "expected_pattern": "json"
    },
    "throughput_sustained": {
        "description": "Sustained generation for throughput testing",
        "prompt": "List 10 common programming languages, one per line:",
        "max_tokens": 150,
        "expected_pattern": "list"
    },
    "memory_bandwidth": {
        "description": "Large memory bandwidth test",
        "prompt": "Generate a comma-separated list of the first 30 even numbers:",
        "max_tokens": 200,
        "expected_pattern": "sequence"
    }
}


class BenchmarkError(Exception):
    """Raised when benchmark execution fails."""
    pass


class APIConnectionError(Exception):
    """Raised when API connection fails."""
    pass


class BenchmarkCore:
    """
    Core benchmark orchestration for llama.cpp API.

    Handles API communication, test execution, and results aggregation.
    Metrics collection is delegated to collector classes.
    """

    def __init__(self, host: str = "localhost", port: int = 8001,
                 timeout: int = 30, label: Optional[str] = None):
        """
        Initialize benchmark core.

        Args:
            host: API host address
            port: API port number
            timeout: Request timeout in seconds
            label: Optional benchmark label (e.g., "baseline", "hugepages")
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.label = label

    def wait_for_api(self, max_attempts: int = 30) -> bool:
        """
        Wait for API to become available.

        Args:
            max_attempts: Maximum number of connection attempts

        Returns:
            True if API responds successfully, False if timeout

        Raises:
            APIConnectionError: If API connection fails after max attempts
        """
        print(f"API connection check: {self.base_url}")

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(f"{self.base_url}/v1/models", timeout=2)
                if response.status_code == 200:
                    print(f"API status: {STATUS_OK} (connected after {attempt} attempts)")
                    return True
            except (requests.RequestException, requests.Timeout):
                pass

            if attempt % 10 == 0:
                print(f"API connection: {STATUS_WARN} (attempt {attempt}/{max_attempts})")

            time.sleep(2)

        print(f"API status: {STATUS_ERROR} (timeout after {max_attempts} attempts)")
        return False

    def get_model_name(self) -> str:
        """
        Get model name from API.

        Returns:
            Model identifier string
        """
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [{}])[0].get("id", "unknown")
        except (requests.RequestException, requests.Timeout, KeyError):
            pass
        return "unknown"

    def run_single_test(self, prompt_key: str, prompt_data: Dict[str, Any],
                       run_num: int) -> Dict[str, Any]:
        """
        Execute a single benchmark test.

        Args:
            prompt_key: Identifier for the test prompt
            prompt_data: Dictionary containing prompt configuration
            run_num: Run number for tracking

        Returns:
            Dictionary containing test results:
            - prompt: Test prompt identifier
            - run: Run number
            - success: Whether test completed successfully
            - total_time: Total execution time in seconds
            - tokens_per_second: Calculated throughput
            - response: Generated response text

        Raises:
            BenchmarkError: If test execution fails
        """
        request_data = {
            "model": "model",
            "messages": [{"role": "user", "content": prompt_data["prompt"]}],
            "max_tokens": prompt_data["max_tokens"],
            "temperature": 0.1,
            "stream": False
        }

        try:
            start_time = time.perf_counter()
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                timeout=self.timeout
            )
            end_time = time.perf_counter()

            if response.status_code != 200:
                return {
                    "prompt": prompt_key,
                    "run": run_num,
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }

            data = response.json()
            total_time = end_time - start_time

            # Extract metrics
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)

            tokens_per_second = completion_tokens / total_time if total_time > 0 else 0

            response_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            return {
                "prompt": prompt_key,
                "run": run_num,
                "success": True,
                "total_time": round(total_time, 3),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "tokens_per_second": round(tokens_per_second, 2),
                "response_length": len(response_content),
                "response": response_content
            }

        except requests.Timeout:
            return {
                "prompt": prompt_key,
                "run": run_num,
                "success": False,
                "error": "request timeout"
            }
        except (requests.RequestException, KeyError, ValueError) as e:
            return {
                "prompt": prompt_key,
                "run": run_num,
                "success": False,
                "error": str(e)
            }

    def run_benchmark(self, num_runs: int = 5, prompts: Optional[List[str]] = None,
                     collectors: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute complete benchmark suite.

        Args:
            num_runs: Number of test runs per prompt
            prompts: List of prompt keys to test (all if None)
            collectors: List of metrics collector instances

        Returns:
            Dictionary containing complete benchmark results:
            - system_info: System configuration information
            - prompts: Per-prompt results and statistics
            - summary: Overall performance summary

        Raises:
            BenchmarkError: If benchmark execution fails
        """
        if prompts is None:
            prompts = list(BENCHMARK_PROMPTS.keys())

        if collectors is None:
            collectors = []

        print("Llama.cpp CPU performance benchmark")
        print()

        # Collect system info from collectors
        system_info = {
            "timestamp": datetime.now().isoformat(),
            "label": self.label,
            "api_url": self.base_url,
            "model": self.get_model_name()
        }

        for collector in collectors:
            if hasattr(collector, 'get_system_info'):
                system_info.update(collector.get_system_info())

        print(f"Model: {system_info.get('model', 'unknown')}")
        print(f"Benchmark configuration: {num_runs} runs per prompt")
        print(f"Timestamp: {system_info['timestamp']}")
        print()

        # Start metrics collection
        for collector in collectors:
            if hasattr(collector, 'start'):
                collector.start()

        all_results = {
            "system_info": system_info,
            "prompts": {},
            "summary": {}
        }

        for prompt_key in prompts:
            if prompt_key not in BENCHMARK_PROMPTS:
                print(f"Prompt validation: {STATUS_ERROR} (unknown prompt: {prompt_key})")
                continue

            prompt_data = BENCHMARK_PROMPTS[prompt_key]
            print(f"Testing prompt: {prompt_key}")
            print(f"  Description: {prompt_data['description']}")

            results = []

            # Warmup run
            print(f"  Warmup: ", end="")
            warmup_result = self.run_single_test(prompt_key, prompt_data, 0)
            warmup_status = STATUS_OK if warmup_result["success"] else STATUS_WARN
            print(f"{warmup_status}")

            # Actual runs
            successful_runs = 0
            for run in range(1, num_runs + 1):
                result = self.run_single_test(prompt_key, prompt_data, run)
                results.append(result)
                if result["success"]:
                    successful_runs += 1

            run_status = STATUS_OK if successful_runs == num_runs else STATUS_WARN if successful_runs > 0 else STATUS_ERROR
            print(f"  Test runs: {run_status} ({successful_runs}/{num_runs} successful)")

            # Calculate statistics for successful runs
            successful_test_results = [r for r in results if r["success"]]
            if successful_test_results:
                tokens_per_sec = [r["tokens_per_second"] for r in successful_test_results]
                avg_tokens_per_sec = round(statistics.mean(tokens_per_sec), 2)
                all_results["prompts"][prompt_key] = {
                    "prompt_text": prompt_data["prompt"],
                    "description": prompt_data["description"],
                    "results": results,
                    "stats": {
                        "success_rate": len(successful_test_results) / len(results),
                        "avg_tokens_per_second": avg_tokens_per_sec,
                        "median_tokens_per_second": round(statistics.median(tokens_per_sec), 2),
                        "min_tokens_per_second": round(min(tokens_per_sec), 2),
                        "max_tokens_per_second": round(max(tokens_per_sec), 2),
                        "stdev_tokens_per_second": round(statistics.stdev(tokens_per_sec), 2) if len(tokens_per_sec) > 1 else 0
                    }
                }
                print(f"  Performance: {STATUS_OK} ({avg_tokens_per_sec} tokens/sec average)")
            else:
                all_results["prompts"][prompt_key] = {
                    "prompt_text": prompt_data["prompt"],
                    "description": prompt_data["description"],
                    "results": results,
                    "stats": {"success_rate": 0}
                }
                print(f"  Performance: {STATUS_ERROR} (all test runs failed)")

        # Stop metrics collection
        for collector in collectors:
            if hasattr(collector, 'stop'):
                metrics = collector.stop()
                if metrics:
                    all_results["summary"].update(metrics)

        # Overall summary
        all_tokens_per_sec = []
        for prompt_key in all_results["prompts"]:
            stats = all_results["prompts"][prompt_key]["stats"]
            if "avg_tokens_per_second" in stats:
                all_tokens_per_sec.append(stats["avg_tokens_per_second"])

        if all_tokens_per_sec:
            overall_avg = round(statistics.mean(all_tokens_per_sec), 2)
            all_results["summary"]["overall_avg_tokens_per_second"] = overall_avg
            all_results["summary"]["overall_median_tokens_per_second"] = round(statistics.median(all_tokens_per_sec), 2)
            all_results["summary"]["overall_min_tokens_per_second"] = round(min(all_tokens_per_sec), 2)
            all_results["summary"]["overall_max_tokens_per_second"] = round(max(all_tokens_per_sec), 2)

            print()
            print(f"Benchmark summary: {STATUS_OK} ({overall_avg} tokens/sec overall average)")
        else:
            print(f"Benchmark summary: {STATUS_ERROR} (no successful test runs)")

        return all_results
