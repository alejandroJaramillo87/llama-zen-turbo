"""
Modular benchmark framework for llama.cpp inference performance testing.

This package provides extensible CPU/GPU metrics collection and analysis
for evaluating zen5_optimizer performance improvements.
"""

from .core import BenchmarkCore, BENCHMARK_PROMPTS
from .constants import (
    STATUS_OK,
    STATUS_WARN,
    STATUS_ERROR,
    STATUS_INFO,
    EXIT_SUCCESS,
    EXIT_FAILURE,
    EXIT_INVALID_USAGE
)

__all__ = [
    'BenchmarkCore',
    'BENCHMARK_PROMPTS',
    'STATUS_OK',
    'STATUS_WARN',
    'STATUS_ERROR',
    'STATUS_INFO',
    'EXIT_SUCCESS',
    'EXIT_FAILURE',
    'EXIT_INVALID_USAGE'
]
