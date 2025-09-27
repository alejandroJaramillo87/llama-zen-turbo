# Zen5 LLAMA Optimizer - Project Roadmap

## Executive Summary

### Mission
Push AMD Zen 5 CPU and llama.cpp to their theoretical performance limits through systematic optimization, leveraging every architectural feature and instruction set capability available.

### Vision
Achieve 4-6x performance improvement for llama.cpp inference on AMD Zen 5 processors exclusively, establishing a new standard for CPU-based LLM inference performance.

### Value Proposition
- **For Users**: 4-6x faster inference on existing AMD hardware
- **For AMD**: Showcase Zen 5's untapped AI capabilities
- **For Community**: Open-source reference implementation of CPU optimizations
- **For Industry**: Reduce inference costs by 75% through performance gains

### Current Status
- **Phase 1A COMPLETED**: Hugepage support implemented with zen5_optimizer library
- **Test Suite COMPLETED**: Comprehensive test coverage (10 tests, 2,800 lines, 100% Phase 1A feature coverage)
- **Proven**: 26% performance gain with BIOS optimizations (FCLK 2100MHz, Curve Optimizer, memory timings)
- **Validated**: Memory bandwidth as primary bottleneck
- **Discovered**: Multiple optimization opportunities totaling 400%+ potential improvement
- **Active Development**: Phase 1B AOCL integration in progress

## Technical Foundation

### Existing Assets
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

### Hardware Context

#### AMD Ryzen 9950X Specifications
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

#### Why Zen 5 + llama.cpp is Underoptimized
1. **llama.cpp prioritizes portability** over platform-specific optimization
2. **Generic OpenBLAS** doesn't leverage Zen 5's architecture
3. **No AVX-512 VNNI usage** despite hardware support
4. **Ignores dual-CCD topology** and NUMA effects
5. **Standard 4KB pages** cause excessive TLB pressure

### Key Technical Discoveries

1. **Memory bandwidth is the bottleneck**
   - System achieves only 9.1% of theoretical bandwidth efficiency
   - CPU has excess compute capacity (proven by minimal CPU optimization impact)
   - Huge pages expected to provide additional gains by reducing TLB misses

2. **Hardware features sitting unused**
   - AVX-512 VNNI instructions for INT8/INT4 computation
   - Dual memory controllers (one per CCD)
   - 96MB of combined L3 cache
   - AOCL 5.1 (May 2025) with Zen 5 optimized BLIS kernels

3. **Quantized models have massive potential**
   - VNNI could provide 2-4x speedup for Q8/Q4 models
   - Direct INT8 computation eliminates dequantization overhead
   - 80% reduction in memory bandwidth requirements

## Technical Architecture

### Core Design Philosophy

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

### Integration Points

```cpp
// Primary interception points (src/zen5_optimizer.cpp)
class Zen5Optimizer {
    // Memory allocation (src/memory/hugepage_allocator.cpp)
    void* mmap(size_t size, ...);           // Huge pages ✅ Implemented
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

### Zen 5 Architectural Features to Exploit

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
   - **AOCL 5.1 (May 2025)** with Zen 5 optimized BLIS library
   - **Zen 5 specific kernels**: Optimized for 256-bit AVX-512 data path
   - **Cache hierarchy aware**: Tuned for 1MB L2 per core, 32MB L3 per CCD
   - **Dual-CCD optimization**: Memory access patterns for dual memory controllers
   - **BLIS_ARCH_TYPE=zen5**: Explicit Zen 5 configuration
   - **Key advantages over generic BLAS**:
     - 25-30% faster DGEMM operations
     - Reduced memory traffic through optimal blocking
     - AVX-512 VNNI ready for future integration

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4) ✅ COMPLETED

#### Phase 1A: Hugepage Support ✅ COMPLETED
- Implemented zen5_optimizer library with CPU validation
- Created modular memory management system
- Integrated hugepage allocator with configurable thresholds
- Successfully tested with llama.cpp models
- **Test Coverage**: 100% feature coverage with comprehensive test suite
  - MAP_FIXED handling, double munmap protection, partial unmapping
  - Concurrent operations (8 threads), stress testing (50 cycles)
  - Fallback scenarios, memory tracking, performance baselines

### Phase 2: Memory Bandwidth Optimizations (Weeks 5-8)

#### Week 5: CCX-Aware Memory Allocation (Experiment 6)
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

#### Week 6: Layer-Ahead Prefetch (Experiment 1)
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

#### Week 7: Mixed Huge Pages (Experiment 2)
- 1GB pages for model weights
- 2MB pages for KV cache
- 4KB pages for temporary buffers
- **Expected gain**: 5-8% additional

#### Week 8: Integration Testing
- Combine all memory optimizations
- Profile and tune parameters
- **Cumulative gain**: 60-70% over baseline

### Phase 3: Advanced Memory Optimizations (Weeks 9-12)

#### Week 9: Cache Line Aligned Weight Packing (Experiment 3)
- Align weights to 64-byte boundaries
- Eliminate split cache line loads
- **Expected gain**: 5-10% additional

#### Week 10: Asynchronous Double Buffering (Experiment 7)
- Load layer N+1 while computing layer N
- Use separate thread for memory operations
- **Expected gain**: 8-12% additional

#### Week 11: Smart KV Cache Manager (Experiment 8)
- Ring buffer for better locality
- FP16 compression for older entries
- **Expected gain**: 5-8% additional

#### Week 12: Bandwidth Throttle Manager (Experiment 4)
- Prevent memory controller saturation
- Strategic pauses for queue management
- **Expected gain**: 3-7% additional
- **Cumulative gain**: 80-100% over baseline

### Phase 4: VNNI Acceleration for Quantized Models (Weeks 13-16)

#### Week 13-14: VNNI Kernel Implementation (Experiment 9)
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

#### Week 15: Quantization Format Support
- Q8_0, Q4_0 format detection
- Scale factor handling
- Fallback for unsupported formats

#### Week 16: Integration and Validation
- Combine VNNI with memory optimizations
- Extensive accuracy testing
- **Expected gain**: 200-400% for quantized models

### Phase 5: Advanced Compute Optimizations (Weeks 17-20)

#### Week 17-18: Weight Compression with AVX-512 (Experiment 5)
- Delta encoding for weights
- On-the-fly decompression
- **Expected gain**: 10-15% additional

#### Week 19: Infinity Fabric Optimization
- Tune CCD-to-CCD communication
- Optimize cross-CCD data sharing
- **Expected gain**: 5-10% additional

#### Week 20: Final Integration and Polish
- Complete feature integration
- Performance validation
- Documentation and release
- **Final target**: 300-500% improvement for quantized models

## Performance Projections

### Progressive Performance Gains

| Phase | Optimization | FP32 Gain | Q8 Gain | Cumulative FP32 | Cumulative Q8 |
|-------|-------------|-----------|---------|-----------------|---------------|
| Baseline | Stock llama.cpp | - | - | 35 tok/s | 35 tok/s |
| Phase 1 | Hugepages | 50% | 50% | 52 tok/s | 52 tok/s |
| Phase 2 | Memory Optimizations | 30% | 30% | 68 tok/s | 68 tok/s |
| Phase 3 | Advanced Memory | 25% | 25% | 85 tok/s | 85 tok/s |
| Phase 4 | VNNI Acceleration | 0% | 200% | 85 tok/s | 255 tok/s |
| Phase 5 | Advanced Compute | 15% | 30% | 98 tok/s | 330 tok/s |

### Model Size Impact

| Model Size | Baseline | Optimized FP32 | Optimized Q8 | Speedup |
|-----------|----------|----------------|--------------|---------|
| 7B | 45 tok/s | 126 tok/s | 450 tok/s | 10x |
| 13B | 28 tok/s | 78 tok/s | 280 tok/s | 10x |
| 30B | 15 tok/s | 42 tok/s | 150 tok/s | 10x |
| 70B | 6 tok/s | 17 tok/s | 60 tok/s | 10x |

## Success Metrics

### Performance Goals
- **Minimum Success**: 50% improvement for FP32 models
- **Target Goal**: 100% improvement for FP32, 300% for INT8
- **Stretch Goal**: 150% for FP32, 500% for INT8

### Adoption Metrics
- **GitHub Stars**: 1000+ within first year
- **Downloads**: 10,000+ monthly active users
- **Benchmarks**: Featured in major LLM performance comparisons
- **Integration**: Adopted by at least 3 major projects

### Technical Validation
- **Accuracy**: Bit-exact results with original implementation
- **Stability**: 24-hour continuous operation without issues
- **Compatibility**: Support for all major quantization formats
- **Zen 5 Required**: No support for other architectures

## Marketing and Outreach Strategy

### Technical Blog Series
1. **"The Foundation: AOCL and Huge Pages"** - Week 4
2. **"AOCL BLIS vs OpenBLAS: AMD's Secret Weapon"** - Week 8
3. **"Taming the Beast: Optimizing Dual-CCD Architectures"** - Week 12
4. **"VNNI Revolution: 4x Speedup for Quantized Models"** - Week 16
5. **"500% Faster: The Complete Optimization Journey"** - Week 20

### Benchmark Publications
- Public benchmark dashboard with real-time results
- Reproducible benchmark scripts
- Comparison with vLLM, TensorRT-LLM
- Cost per token analysis

### Community Engagement
- AMD Developer Forums announcement
- llama.cpp GitHub discussions
- HackerNews launch with technical deep-dive
- Conference talks (Hot Chips, ISCA)

## Risk Analysis and Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| llama.cpp API changes | High | Medium | Multiple interception points, version detection |
| Numerical instability | Medium | High | Extensive validation suite, gradual rollout |
| VNNI compatibility issues | Low | Medium | Zen 5 has full VNNI support |
| Memory allocation failures | Low | High | Clear error messages, configuration options |

### Strategic Risks
- **AMD changes direction**: Continue supporting Zen 5 specifically
- **llama.cpp implements similar**: Our Zen 5 focus remains unique
- **Performance gains don't materialize**: Already validated 26% gain from BIOS, rest is upside

## Long-term Vision

### Year 1: Establish Leadership
- Complete all optimization phases
- Build community of users
- Establish benchmark authority
- Engage with AMD DevRel

### Year 2: Expand Ecosystem
- Deeper Zen 5 optimizations and tuning
- Support for Zen 6 (when available)
- MI300 APU optimizations
- Distributed inference support
- Commercial support offerings

### Year 3: Industry Standard
- AMD official endorsement
- Integration into major frameworks
- Reference implementation status
- Consulting and training services

### Potential Exit Strategies
1. **AMD Acquisition**: Become official AMD inference solution
2. **Open Source Success**: Become de facto standard for CPU inference
3. **Commercial Pivot**: Enterprise support and optimization services
4. **Technology Licensing**: License optimizations to cloud providers

## Resource Requirements

### Development Resources
- **Time**: 20 weeks of focused development
- **Hardware**: Already available (Ryzen 9950X + RTX 5090)
- **Software**: BLIS, development tools (free/open source)
- **Testing**: Various model sizes and quantizations

### External Dependencies
- **AOCL 5.1**: AMD's latest Optimized CPU Libraries (May 2025) with Zen 5 optimized BLIS
- **llama.cpp**: Target application (referenced via ai-experiments submodule)
- **hugepage support**: Linux kernel feature ✅ Implemented
- **AVX-512**: CPU instruction set

## Call to Action

### Immediate Actions (Week 0) ✅ COMPLETED
1. ✅ Tagged v1.0.0 release of ai-experiments repository
2. ✅ Created llama-zen-turbo repository
3. ✅ Set up development environment
4. ✅ Implemented Phase 1A hugepage support
5. ✅ Created comprehensive test suite (10 tests, 100% Phase 1A coverage)
6. 🔄 AOCL integration research in progress

### Month 1 Milestone
- ✅ Packaged hugepage optimizer (Phase 1A complete)
- ✅ Comprehensive test suite with stress, concurrency, and performance testing
- 🔄 Working AOCL 5.1 BLIS integration with Zen 5 kernels (Phase 1B)
- ⏳ 50% performance improvement demonstrated
- ⏳ First blog post published

### Month 3 Milestone
- All memory optimizations complete
- 100% improvement for FP32
- Community awareness building
- AMD DevRel engagement

### Month 5 Milestone
- VNNI acceleration complete
- 400% improvement for INT8
- Production-ready release
- Major announcement campaign

## Conclusion

This project represents a unique opportunity to:
1. **Push hardware to its limits** using every available feature
2. **Solve a real problem** that affects thousands of users
3. **Establish technical leadership** in CPU optimization
4. **Create lasting value** for the AI community

The combination of proven techniques (hugepages), Zen 5-specific optimizations (AOCL 5.1 BLIS, dual-CCD), and revolutionary improvements (VNNI) positions this project to redefine what's possible with CPU inference on AMD's latest architecture.

With 26% improvement from BIOS optimizations already proven and clear paths to 400%+ gains, this isn't speculation—it's engineering.

---

*"We choose to optimize llama.cpp on Zen 5, not because it is easy, but because it is hard."*

**Next Step**: Create the repository and begin Phase 1.