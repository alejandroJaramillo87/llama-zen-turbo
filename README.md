# llama-zen-turbo

AMD Zen 5 optimizer for llama.cpp - transparent performance improvements via LD_PRELOAD.

## Overview

This project provides architecture-specific optimizations for running llama.cpp on AMD Zen 5 processors (Ryzen 9000 series, Ryzen AI 300 series). It achieves significant speedup through:

- Transparent huge page allocation for model files
- BLIS integration with Zen 5 optimized kernels (Phase 2)
- CCX-aware NUMA optimization (Phase 3)
- AVX-512 VNNI for INT8 operations (Phase 4)

## Current Status

Phase 1A implemented: Basic hugepage support for reducing TLB pressure during model loading.
- Comprehensive test suite completed (10 tests, 100% Phase 1A coverage)
- Performance baselines established for optimization tracking

## Requirements

- AMD Zen 5 processor (Family 25h)
- Linux x86_64
- GCC with C++17 support
- Huge pages enabled in kernel

## Building

```bash
make                # Build library
make test          # Run all tests (verbose)
make test-quiet    # Run tests with minimal output
make install       # Install to /usr/local/lib
```

## Usage

```bash
# Load optimizer before running llama.cpp
LD_PRELOAD=/usr/local/lib/libzen5_optimizer.so ./llama.cpp [args]

# Or export for session
export LD_PRELOAD=/usr/local/lib/libzen5_optimizer.so
./llama.cpp [args]
```

## Relationship to ai-experiments

This project builds on proven components from the `ai-experiments` repository (included as `external/ai-experiments`):

- Inherits hugepage wrapper implementation
- Follows established style guides for Linux system programming
- Uses benchmark utilities for performance validation

The ai-experiments submodule provides battle-tested infrastructure while this repository focuses specifically on AMD Zen 5 optimizations.

## Architecture

```
src/
├── zen5_optimizer.cpp      # Main LD_PRELOAD entry point
├── cpu_validator.cpp       # AMD Zen 5 detection
├── memory/
│   └── hugepage_wrapper.cpp # mmap() interception
└── config.h                # Configuration parameters

tests/
├── unit/                   # Basic functionality tests
│   ├── test_load.cpp       # Library loading
│   ├── test_cpu.cpp        # CPU detection
│   └── test_hugepage.cpp   # mmap interception
├── functional/             # Feature-level tests
│   ├── test_memory_boundaries.cpp  # 1GB threshold testing
│   ├── test_munmap.cpp            # Allocation tracking
│   ├── test_fallback.cpp          # Graceful degradation
│   ├── test_memory_tracking.cpp   # Memory management
│   ├── test_stress.cpp            # High-load scenarios
│   └── test_performance.cpp       # Baseline measurements
└── integration/            # End-to-end validation
```

## Performance

Phase 1A provides baseline optimizations. Full performance targets:
- Minimum: 50% improvement for FP32 operations
- Target: 400% improvement for INT8/Q4 quantized models

Current BIOS optimizations provide 26% gain (FCLK 2100MHz, Curve Optimizer).
Performance baselines established through comprehensive stress and throughput testing.

## Development

This is a Zen 5 exclusive project - no fallbacks or compatibility layers. The library will refuse to load on non-Zen 5 CPUs.

See `docs/ZEN5_OPTIMIZER_ROADMAP.md` for detailed development phases.