#!/usr/bin/env python3
"""
CPU-specific benchmark for llama.cpp inference performance.

Measures tokens per second and collects CPU/memory metrics including:
- TLB miss rates (hugepage impact analysis)
- Cache miss rates
- Page fault statistics
- Hugepage utilization

Usage (run from repo root):
    python scripts/benchmark_cpu.py --label baseline --output baseline.json
    python scripts/benchmark_cpu.py --label hugepages --runs 10
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add repo root to Python path for benchmark package import
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.core import BenchmarkCore, BenchmarkError, APIConnectionError
from benchmark.constants import EXIT_SUCCESS, EXIT_FAILURE
from benchmark.collectors import (
    PerfCollector,
    VmstatCollector,
    HugepageCollector,
    CPUInfoCollector
)


def print_summary(results: Dict[str, Any]) -> None:
    """
    Print comprehensive benchmark results summary.

    Args:
        results: Complete benchmark results dictionary
    """
    print()
    print("=" * 60)
    print("Benchmark Results Summary")
    print("=" * 60)

    # Print label if present
    if "system_info" in results and results["system_info"].get("label"):
        print(f"\nBenchmark label: {results['system_info']['label']}")

    # CPU info
    if "system_info" in results and "cpu" in results["system_info"]:
        cpu = results["system_info"]["cpu"]
        print(f"\nCPU: {cpu.get('cpu_model', 'unknown')}")
        if cpu.get("is_zen5"):
            print("  Architecture: AMD Zen 5 ✓")
        print(f"  Cores/Threads: {cpu.get('cpu_cores', '?')}/{cpu.get('cpu_threads', '?')}")

    # Hugepage info
    if "system_info" in results and "hugepages" in results["system_info"]:
        hp = results["system_info"]["hugepages"]
        if "hugepages_used" in hp:
            print(f"\nHugepages: {hp['hugepages_used']}/{hp['hugepages_total']} pages")
            if "hugepages_used_gb" in hp:
                print(f"  Used: {hp['hugepages_used_gb']} GB ({hp['hugepage_size_kb']/1024:.0f} MB pages)")

    # Per-prompt results
    print("\n" + "-" * 60)
    print("Per-Prompt Performance")
    print("-" * 60)
    print(f"{'Prompt':<25} {'Tokens/sec':>15} {'Success':>12}")
    print("-" * 60)

    for prompt_key in results["prompts"]:
        stats = results["prompts"][prompt_key]["stats"]
        avg_tps = stats.get("avg_tokens_per_second", 0)
        success_rate = stats.get("success_rate", 0) * 100
        print(f"{prompt_key:<25} {avg_tps:>15.2f} {success_rate:>11.0f}%")

    # Overall summary
    if "summary" in results and "overall_avg_tokens_per_second" in results["summary"]:
        print("-" * 60)
        print(f"{'Overall Average':<25} {results['summary']['overall_avg_tokens_per_second']:>15.2f}")
        print(f"{'Median':<25} {results['summary']['overall_median_tokens_per_second']:>15.2f}")
        print(f"{'Range':<25} {results['summary']['overall_min_tokens_per_second']:>6.2f} - {results['summary']['overall_max_tokens_per_second']:<6.2f}")

    # Perf metrics
    if "summary" in results and "perf" in results["summary"]:
        perf = results["summary"]["perf"]
        print("\n" + "-" * 60)
        print("Performance Counter Metrics")
        print("-" * 60)

        if "ipc" in perf:
            print(f"Instructions per cycle: {perf['ipc']}")

        if "dTLB_miss_rate" in perf:
            print(f"dTLB miss rate: {perf['dTLB_miss_rate']:.3f}%")

        if "iTLB_miss_rate" in perf:
            print(f"iTTLB miss rate: {perf['iTLB_miss_rate']:.3f}%")

        if "cache_miss_rate" in perf:
            print(f"Cache miss rate: {perf['cache_miss_rate']:.2f}%")

    # Vmstat metrics
    if "summary" in results and "vmstat" in results["summary"]:
        vmstat = results["summary"]["vmstat"]
        print("\n" + "-" * 60)
        print("Page Fault Statistics")
        print("-" * 60)

        if "pgfault_delta" in vmstat:
            print(f"Page faults: {vmstat['pgfault_delta']:,}")

        if "pgmajfault_delta" in vmstat:
            print(f"Major faults: {vmstat['pgmajfault_delta']:,}")

        if "thp_fault_alloc_delta" in vmstat:
            print(f"THP allocations: {vmstat['thp_fault_alloc_delta']:,}")

    print("=" * 60)


def save_results(results: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Save benchmark results to JSON file.

    Args:
        results: Complete benchmark results dictionary
        filename: Output filename (auto-generated if None)

    Returns:
        Path to saved results file

    Raises:
        BenchmarkError: If file cannot be saved
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = results.get("system_info", {}).get("label", "benchmark")
        filename = f"results/{label}_{timestamp}.json"

    try:
        # Ensure parent directory exists
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved: {filename}")
        return str(filename)
    except (IOError, OSError) as e:
        raise BenchmarkError(f"Failed to save results to {filename}: {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="CPU-specific llama.cpp inference benchmark with TLB/cache metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Baseline benchmark (no hugepages)
  python scripts/benchmark_cpu.py --label baseline --output results/baseline.json

  # Optimized benchmark (with hugepages)
  python scripts/benchmark_cpu.py --label hugepages --runs 10

  # Quick test with specific prompts
  python scripts/benchmark_cpu.py --prompts memory_sequential,compute_arithmetic --runs 3

  # Custom container
  python scripts/benchmark_cpu.py --container my-llama --port 8002
        """
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="API host address (default: localhost)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="API port number (default: 8001)"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of test runs per prompt (default: 5)"
    )

    parser.add_argument(
        "--prompts",
        help="Comma-separated list of prompts to test (default: all)"
    )

    parser.add_argument(
        "--output",
        help="Output JSON filename (default: results/<label>_<timestamp>.json)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )

    parser.add_argument(
        "--label",
        required=True,
        help="Benchmark label (e.g., baseline, hugepages, optimized)"
    )

    parser.add_argument(
        "--container",
        default="llama-zen5",
        help="Docker container name for perf monitoring (default: llama-zen5)"
    )

    parser.add_argument(
        "--no-perf",
        action="store_true",
        help="Disable perf stat collection (useful if no permissions)"
    )

    return parser


def main() -> int:
    """
    Main function to execute CPU benchmark.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Parse prompts if specified
        prompts = None
        if args.prompts:
            prompts = [p.strip() for p in args.prompts.split(",")]

        # Create benchmark instance
        benchmark = BenchmarkCore(
            host=args.host,
            port=args.port,
            timeout=args.timeout,
            label=args.label
        )

        # Wait for API
        if not benchmark.wait_for_api():
            print("ERROR: API not responding", file=sys.stderr)
            print("  Solution: Verify container is running with 'docker ps'", file=sys.stderr)
            return 1

        # Initialize collectors
        collectors = [
            HugepageCollector(),
            CPUInfoCollector(),
            VmstatCollector()
        ]

        # Add perf collector if not disabled
        if not args.no_perf:
            collectors.append(PerfCollector(container_name=args.container))

        # Run benchmark
        results = benchmark.run_benchmark(
            num_runs=args.runs,
            prompts=prompts,
            collectors=collectors
        )

        # Print summary
        print_summary(results)

        # Save results
        save_results(results, args.output)

        return 0

    except BenchmarkError as e:
        print(f"ERROR: Benchmark execution failed: {e}", file=sys.stderr)
        return 1
    except APIConnectionError as e:
        print(f"ERROR: API connection failed: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
