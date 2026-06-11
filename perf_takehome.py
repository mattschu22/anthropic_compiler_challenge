"""Compatibility entrypoint for the perf take-home submission.

The implementation lives in ``anthropic_compiler_challenge`` so the code is
easier to navigate. This module preserves the original public import used by
``submission_tests.py`` and grader-style harnesses.
"""

from anthropic_compiler_challenge import (
    KernelBuilder,
    do_kernel_test,
    hyperparameter_search,
    test_kernel_cycles,
)

__all__ = [
    "KernelBuilder",
    "do_kernel_test",
    "hyperparameter_search",
    "test_kernel_cycles",
]


if __name__ == "__main__":
    print(do_kernel_test(10, 16, 256, trace=True))
