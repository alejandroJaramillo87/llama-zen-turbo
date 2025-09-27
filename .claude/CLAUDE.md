  # llama-zen-turbo - AMD Zen 5 Optimizer for llama.cpp

  ## Project Context

  This repository implements high-performance optimizations for llama.cpp specifically targeting AMD Zen 5 processors. It achieves 4-6x speedup through architecture-specific
  optimizations.

  ## Relationship to ai-experiments

  This project uses `ai-experiments` as a submodule (in `external/`) for:
  - Base infrastructure and tooling
  - Proven hugepage wrapper implementation
  - Benchmark utilities
  - Style guides and documentation standards

  ## Style Guides

  This project inherits all style guides from ai-experiments:
  - See `includes/BASH_OUTPUT_STYLE.md` for bash output formatting
  - See `includes/PYTHON_STYLE.md` for Python coding standards
  - See `includes/COMMENT_STYLE.md` for comment conventions
  - See `includes/DOCUMENTATION_STYLE.md` for documentation standards

  ## Zen 5 Specific Development

  ### Target Architecture
  - **ONLY** AMD Zen 5 (family 25h)
  - No fallbacks or compatibility layers
  - Exit with clear error if not Zen 5

  ### Key Optimizations
  1. **AOCL 5.1 BLIS Integration**: AMD AOCL 5.1 (May 2025) with Zen 5 optimized BLIS kernels
  2. **Hugepage Allocation**: From ai-experiments wrapper
  3. **CCX-Aware NUMA**: Dual-CCD optimization
  4. **AVX-512 VNNI**: Direct INT8 computation
  5. **Memory Prefetching**: Layer-ahead prefetch

  ### Performance Goals
  - Minimum: 50% improvement for FP32
  - Target: 400% improvement for INT8/Q4

  ### Important Development Notes
  - Using AOCL 5.1 (latest, May 2025) for BLIS implementation
  - Test only on Zen 5 hardware
  - No generic x86 fallbacks