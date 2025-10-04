# Zen 5 LLAMA optimizer project roadmap

## Table of Contents

- [Executive Summary](#executive-summary)
- [Performance Baseline Clarification](#performance-baseline-clarification)
- [Technical Foundation](#technical-foundation)
- [Key Technical Discoveries](#key-technical-discoveries)
- [Memory Bandwidth Physics](#memory-bandwidth-physics-the-hard-constraint)
- [Technical Architecture](#technical-architecture)
- [Implementation Roadmap](#implementation-roadmap)
  - [Phase 1: Foundation](#phase-1-foundation-weeks-1-4--completed)
  - [Phase 2: Memory Bandwidth Optimizations](#phase-2-memory-bandwidth-optimizations-weeks-5-8)
  - [Phase 3: Advanced Memory Optimizations](#phase-3-advanced-memory-optimizations-weeks-9-12)
  - [Phase 4: VNNI Acceleration](#phase-4-vnni-acceleration-for-quantized-models-weeks-13-16)
  - [Phase 5: Advanced Compute Optimizations](#phase-5-advanced-compute-optimizations-weeks-17-20)
- [Performance Projections](#performance-projections)
- [Technical Validation](#technical-validation)
- [Dependencies](#dependencies)
- [Current Status](#current-status)

## Executive summary

### Mission
Push AMD Zen 5 CPU and llama.cpp to their theoretical performance limits through systematic optimization, leveraging every architectural feature and instruction set capability available.

### Vision
Achieve 4-6x performance improvement for llama.cpp inference on AMD Zen 5 processors exclusively, establishing a new standard for CPU-based LLM inference performance.

### Value proposition
- **For Users**: 4-6x faster inference on existing AMD hardware
- **For AMD**: Showcase Zen 5's untapped AI capabilities
- **For Community**: Open-source reference implementation of CPU optimizations
- **For Industry**: Reduce inference costs by 75% through performance gains

### Current status
- **Phase 1A COMPLETED**: Hugepage support implemented with zen5_optimizer library
- **Test Suite COMPLETED**: Comprehensive test coverage (10 tests, 2,800 lines, 100% Phase 1A feature coverage)
- **Proven**: 26% performance gain with BIOS optimizations (FCLK 2100MHz, Curve Optimizer, memory timings)
- **Validated**: Memory bandwidth as primary bottleneck
- **Discovered**: Multiple optimization opportunities totaling 400%+ potential improvement
- **Active Development**: Phase 1B AOCL integration in progress

## Performance baseline clarification

**Important**: This project builds on hardware optimizations to deliver software-level gains.

### Hardware baseline (BIOS optimizations)
The validated 26% performance improvement comes from BIOS/firmware optimizations:
- **Original baseline**: 28.09 tokens/second (stock BIOS settings)
- **Optimized baseline**: 35.44 tokens/second (BIOS optimizations enabled)
- **Gain**: 26.2% improvement from hardware configuration

**BIOS optimizations include:**
- FCLK 2100 MHz (Infinity Fabric clock)
- Conservative Curve Optimizer (-15)
- CPU Boost +200 MHz
- C-states disabled
- Memory power-down disabled
- DDR5-6000 tuned timings

### Software baseline (this library)
The zen5_optimizer library **starts from the optimized 35.44 tok/s baseline** and adds:
- **Phase 1A**: Hugepage support (foundation for memory optimizations)
- **Phase 1B+**: AOCL BLIS, NUMA, prefetching, VNNI acceleration

**Key Insight**: All projected performance gains in this roadmap are **additive to** the 26% BIOS improvement, not inclusive of it.

### Performance attribution
```
Stock llama.cpp: 28 tok/s
    + BIOS optimizations: +26%
    = Hardware-optimized: 35 tok/s (SOFTWARE BASELINE)
    + zen5_optimizer library: phases 1-5
    = Target performance: 98-330 tok/s (depending on model quantization)
```

## Technical foundation

### Existing assets
1. **Working hugepage implementation**
   - Original wrapper: `external/ai-experiments/docker/llama-cpu/hugepage_mmap_wrapper.cpp`
   - New Zen5 optimizer: `src/memory/hugepage_allocator.cpp`
   - 26% performance improvement from BIOS optimizations validated
   - MAP_HUGETLB implementation without special filesystems
   - Production-ready code with CPU validation
   - **Comprehensive test suite**: 10 tests covering all critical paths

2. **Comprehensive research** (`external/ai-experiments/docs/optimizations/experiments/`)
   - 9 documented optimization experiments
   - Memory bandwidth analysis showing 9.1% efficiency
   - VNNI acceleration pathway for 2-4x gains

3. **Benchmark infrastructure** (`scripts/benchmark.py`)
   - Reproducible performance testing
   - Multiple workload patterns
   - JSON and human-readable output

4. **Test suite** (`tests/`)
   - 10 executable tests (3 unit, 6 functional, 1 integration)
   - 2,800 lines of test code
   - ~2 seconds full suite execution
   - Covers CPU detection, memory boundaries, concurrency, stress scenarios
   - Performance baselines established for optimization tracking

### Hardware context

#### AMD Ryzen 9950X specifications
- **Architecture**: Zen 5 (4nm process)
- **Cores**: 16 cores / 32 threads
- **Layout**: 2 CCDs (Core Complex Dies), 8 cores each
- **Cache**:
  - L1: 80KB per core (64KB I-cache + 16KB D-cache)
  - L2: 1MB per core (16MB total)
  - L3: 64MB total (32MB per CCD)
- **Memory**: DDR5-6000 support, dual-channel
- **SIMD**: AVX-512 with VNNI support
- **TDP**: 170W (230W max boost)

#### Why Zen 5 + llama.cpp is underoptimized
1. **llama.cpp prioritizes portability** over platform-specific optimization
2. **Generic OpenBLAS** does not leverage Zen 5 architecture
3. **No AVX-512 VNNI usage** despite hardware support
4. **Ignores dual-CCD topology** and NUMA effects
5. **Standard 4KB pages** cause excessive TLB pressure

### Key technical discoveries

1. **Memory bandwidth is the bottleneck**
   - System achieves only 9.1% of theoretical bandwidth efficiency
   - CPU has excess compute capacity (proven by minimal CPU optimization impact)
   - Huge pages expected to provide additional gains by reducing TLB misses

2. **Hardware features sitting unused**
   - AVX-512 VNNI instructions for INT8/INT4 computation
   - Dual memory controllers (one per CCD)
   - 96MB of combined L3 cache
   - AOCL 5.1 with Zen 5 optimized BLIS kernels

3. **Quantized models have massive potential**
   - VNNI could provide 2-4x speedup for Q8/Q4 models
   - Direct INT8 computation eliminates dequantization overhead
   - 80% reduction in memory bandwidth requirements

### Memory bandwidth physics: the hard constraint

**Understanding the 9.1% efficiency and 96GB/s limit:**

```
For a 30GB FP32 model generating tokens at 35 tok/s:

Theoretical bandwidth needed per token:
  - Must read entire model: 30GB × 35 tokens/sec = 1,050 GB/s

Available bandwidth (DDR5-6000 dual-channel):
  - Theoretical maximum: 96 GB/s
  - Real-world achievable: ~70-80 GB/s

Current efficiency:
  - Actual usage: ~8.7 GB/s (measured)
  - Efficiency: 8.7 / 96 = 9.1%
  - Cache reuse factor: ~11× (each byte read 11 times from cache)
```

**Why adding more bandwidth is not possible:**
1. **Physical limit**: DDR5-6000 dual-channel = 96GB/s maximum
2. **Current bottleneck**: Not bandwidth saturation, but poor cache utilization
3. **Optimization strategy**: Improve cache hit rate from 91% to 95%+ (doubles effective bandwidth)

**How optimizations overcome the limit:**
- **Huge pages**: Reduce TLB misses, more L1/L2 TLB hits, fewer page table walks, increases effective bandwidth
- **Prefetching**: Hide memory latency, overlap compute and memory access, increases throughput
- **NUMA interleaving**: Use both memory controllers (2×48GB/s), parallel access, increases bandwidth
- **Compression/VNNI**: Reduce data size (INT8 vs FP32 = 4× smaller), reduces bandwidth requirement
- **Cache blocking**: Better locality, higher hit rate, less memory traffic

**The key insight**: We're not trying to exceed 96GB/s. We're trying to use it more efficiently by improving cache hit rates from 91% to 95%+, which effectively doubles throughput without needing more bandwidth.

## Technical architecture

### Core design philosophy

1. **Single Unified Wrapper**
   - One LD_PRELOAD library instead of multiple
   - Central configuration and feature detection
   - Coordinated optimizations that work together

2. **Progressive Enhancement**
   - Detect Zen 5 CPU at startup
   - Enable all optimizations (no conditionals)
   - Exit immediately if not Zen 5

3. **Zero-Copy Integration**
   - Intercept existing llama.cpp calls
   - No modifications to llama.cpp required
   - Compatible with future llama.cpp versions

4. **Zen 5 Exclusivity**
   - CPU detection exits if not Zen 5 (family 25h)
   - No fallbacks or compatibility layers
   - Clear error: "llama-zen-turbo requires AMD Zen 5 processor"

### Integration points

```cpp
// Primary interception points (src/zen5_optimizer.cpp)
class Zen5Optimizer {
    // Memory allocation (src/memory/hugepage_allocator.cpp)
    void* mmap(size_t size, ...);           // Huge pages (implemented)
    void* malloc(size_t size);              // NUMA-aware allocation

    // BLAS operations (Phase 1B)
    void cblas_sgemm(...);                   // Route to AOCL BLIS
    void ggml_compute_forward(...);          // Compute interception

    // Memory operations
    void* memcpy(void* dst, void* src, size_t n);  // Prefetch/streaming

    // Quantized operations
    void dequantize_row_q8_0(...);          // VNNI acceleration
    void ggml_vec_dot_q8_0_q8_0(...);       // Direct INT8 compute
};
```

### Zen 5 architectural features to exploit

1. **Dual CCD Architecture**
   - Independent memory controllers per CCD
   - 32MB L3 cache per CCD
   - Infinity Fabric interconnect

2. **AVX-512 Implementation**
   - 256-bit execution units (double pumped)
   - VNNI for INT8/INT4 operations
   - Efficient masked operations

3. **Memory Hierarchy**
   - 80KB L1 per core (highest in class)
   - 1MB L2 per core (private)
   - Hardware prefetchers

4. **AOCL Optimizations (Zen 5 Specific)**
   - **AOCL 5.1** with Zen 5 optimized BLIS library
   - **Zen 5 specific kernels**: Optimized for 256-bit AVX-512 data path
   - **Cache hierarchy aware**: Tuned for 1MB L2 per core, 32MB L3 per CCD
   - **Dual-CCD optimization**: Memory access patterns for dual memory controllers
   - **BLIS_ARCH_TYPE=zen5**: Explicit Zen 5 configuration
   - **Key advantages over generic BLAS**:
     - 25-30% faster DGEMM operations
     - Reduced memory traffic through optimal blocking
     - AVX-512 VNNI ready for future integration

## Implementation roadmap

### Phase 1: Foundation (weeks 1-4) (completed)

#### Phase 1A: Hugepage support (completed)
- Implemented zen5_optimizer library with CPU validation
- Created modular memory management system
- Integrated hugepage allocator with configurable thresholds
- Successfully tested with llama.cpp models
- **Test Coverage**: 100% feature coverage with comprehensive test suite
  - MAP_FIXED handling, double munmap protection, partial unmapping
  - Concurrent operations (8 threads), stress testing (50 cycles)
  - Fallback scenarios, memory tracking, performance baselines

**Performance Note**: Hugepage support provides the foundation for memory optimizations. Standalone huge pages typically deliver 10-20% TLB efficiency improvement. The full 50% Phase 1 target is achieved when combined with Phase 1B (AOCL BLIS) and subsequent memory access optimizations. Huge pages reduce TLB pressure (7.8M page table entries reduced to 15K entries), enabling other optimizations to work more effectively.

#### Phase 1B: AOCL BLIS integration (in progress)
**Goal**: Replace generic OpenBLAS with AMD's Zen 5-optimized BLIS kernels
**Expected Gain**: 15-25% improvement in GEMM operations
**Status**: Research and integration phase

**Why AOCL BLIS Helps (Memory Perspective)**:
- **Not about raw FLOPS**: System has excess CPU cycles (proven by minimal CPU optimization impact)
- **Cache-aware blocking**: BLIS uses optimal tile sizes for 1MB L2 per core, 32MB L3 per CCD
- **Reduced memory traffic**: Better blocking = higher cache hit rate = less bandwidth consumption
- **Dual-CCD awareness**: Memory access patterns optimized for dual memory controllers
- **Zen 5 specific tuning**: `BLIS_ARCH_TYPE=zen5` enables architecture-specific optimizations

**Implementation Approach**:
```cpp
// Intercept cblas_sgemm and route to AOCL BLIS
extern "C" void cblas_sgemm(...) {
    // Use AOCL BLIS with Zen 5 optimizations
    bli_sgemm(...);  // Zen 5 optimized kernel
}
```

**Key Insight**: AOCL BLIS is a **memory optimization** that improves cache locality and reduces bandwidth pressure, not just a compute speedup. This is why it helps despite excess CPU capacity.

### Phase 2: Memory bandwidth optimizations (weeks 5-8)

#### Week 5: CCX-aware memory allocation (experiment 6)
```cpp
// Distribute memory across both CCDs
void* allocate_interleaved(size_t size) {
    void* ptr = mmap(NULL, size, PROT_READ|PROT_WRITE,
                    MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    unsigned long nodemask = 0x3;  // Both NUMA nodes
    mbind(ptr, size, MPOL_INTERLEAVE, &nodemask, 2, 0);
    return ptr;
}
```
- **Expected gain**: 5-10% additional

#### Week 6: Layer-ahead prefetch (experiment 1)
```cpp
// Prefetch next layer while computing current
void prefetch_next_layer(int current_layer) {
    if (current_layer + 1 < num_layers) {
        void* next_weights = layer_weights[current_layer + 1];
        size_t size = layer_sizes[current_layer + 1];
        for (size_t i = 0; i < size; i += 64) {
            _mm_prefetch((char*)next_weights + i, _MM_HINT_T2);
        }
    }
}
```
- **Expected gain**: 8-12% additional

#### Week 7: Mixed huge pages (experiment 2)
- 1GB pages for model weights
- 2MB pages for KV cache
- 4KB pages for temporary buffers
- **Expected gain**: 5-8% additional

#### Week 8: Integration testing
- Combine all memory optimizations
- Profile and tune parameters
- **Cumulative gain**: 60-70% over baseline

### Phase 3: Advanced memory optimizations (weeks 9-12)

#### Week 9: Cache line aligned weight packing (experiment 3)
- Align weights to 64-byte boundaries
- Eliminate split cache line loads
- **Expected gain**: 5-10% additional

#### Week 10: Asynchronous double buffering (experiment 7)
- Load layer N+1 while computing layer N
- Use separate thread for memory operations
- **Expected gain**: 8-12% additional

#### Week 11: Smart KV cache manager (experiment 8)
- Ring buffer for better locality
- FP16 compression for older entries
- **Expected gain**: 5-8% additional

#### Week 12: Bandwidth throttle manager (experiment 4)
- Prevent memory controller saturation
- Strategic pauses for queue management
- **Expected gain**: 3-7% additional
- **Cumulative gain**: 80-100% over baseline

### Phase 4: VNNI acceleration for quantized models (weeks 13-16)

**Baseline Clarification**: VNNI provides 200-300% speedup on top of optimized Q8 models (35-40 tok/s), not stock llama.cpp. Experimental research showing 10 tok/s baselines measured unoptimized Q8 with dequantization overhead. This phase applies VNNI to already-optimized models from Phases 1-3.

#### Week 13-14: VNNI kernel implementation (experiment 9)
```cpp
// Direct INT8 computation without dequantization
void vnni_int8_gemm(const int8_t* A, const int8_t* B,
                    int32_t* C, int M, int N, int K) {
    for (int m = 0; m < M; m += 4) {
        for (int n = 0; n < N; n += 16) {
            __m512i acc = _mm512_setzero_si512();
            for (int k = 0; k < K; k += 4) {
                __m512i a = _mm512_load_si512(&A[m*K + k]);
                __m512i b = _mm512_load_si512(&B[k*N + n]);
                acc = _mm512_dpbusd_epi32(acc, a, b);
            }
            _mm512_store_si512(&C[m*N + n], acc);
        }
    }
}
```

#### Week 15: Quantization format support
- Q8_0, Q4_0 format detection
- Scale factor handling
- Fallback for unsupported formats

#### Week 16: Integration and validation
- Combine VNNI with memory optimizations
- Extensive accuracy testing
- **Expected gain**: 200-400% for quantized models

### Phase 5: Advanced compute optimizations (weeks 17-20)

#### Week 17-18: Weight compression with AVX-512 (experiment 5)
- Delta encoding for weights
- On-the-fly decompression
- **Expected gain**: 10-15% additional

#### Week 19: Infinity Fabric optimization
- Tune CCD-to-CCD communication
- Optimize cross-CCD data sharing
- **Expected gain**: 5-10% additional

#### Week 20: Final integration and polish
- Complete feature integration
- Performance validation
- Documentation and release
- **Final target**: 300-500% improvement for quantized models

## Performance projections

**Note**: The following projections represent optimistic targets based on theoretical analysis and experimental research. Conservative estimates suggest 50-70% of these gains are achievable. Actual results depend on model size, quantization format, and workload characteristics.

### Progressive performance gains

| Phase | Optimization | FP32 Gain | Q8 Gain | Cumulative FP32 | Cumulative Q8 |
|-------|-------------|-----------|---------|-----------------|---------------|
| Baseline | BIOS-optimized llama.cpp | - | - | 35 tok/s | 35 tok/s |
| Phase 1A | Hugepages (foundation) | 10-20% | 10-20% | 38-42 tok/s | 38-42 tok/s |
| Phase 1B | AOCL BLIS | 15-25% | 15-25% | 44-53 tok/s | 44-53 tok/s |
| Phase 2 | Memory Optimizations | 20-30% | 20-30% | 53-69 tok/s | 53-69 tok/s |
| Phase 3 | Advanced Memory | 15-25% | 15-25% | 61-86 tok/s | 61-86 tok/s |
| Phase 4 | VNNI Acceleration | 0% | 200-300% | 61-86 tok/s | 183-344 tok/s |
| Phase 5 | Advanced Compute | 10-20% | 20-40% | 67-103 tok/s | 220-482 tok/s |

**Projected Outcomes**:
- **FP32 models**: 67-103 tok/s (1.9-2.9× improvement over baseline)
- **Q8 models**: 220-482 tok/s (6.3-13.8× improvement over baseline)
- **Key multiplier**: VNNI acceleration for quantized models provides the largest gains

## Technical validation

- **Accuracy**: Bit-exact results with original implementation
- **Stability**: 24-hour continuous operation without issues
- **Compatibility**: Support for all major quantization formats
- **Zen 5 Required**: No support for other architectures

## Dependencies

- **AOCL 5.1**: AMD Optimized CPU Libraries with Zen 5 optimized BLIS
- **llama.cpp**: Target application (referenced via ai-experiments submodule)
- **hugepage support**: Linux kernel feature (implemented)
- **AVX-512**: CPU instruction set

## Current status

- Phase 1A (hugepage support) completed
- Comprehensive test suite implemented (10 tests, 100% Phase 1A coverage)
- Phase 1B (AOCL 5.1 BLIS integration) in progress

---

*Last Updated: 2025-10-03*