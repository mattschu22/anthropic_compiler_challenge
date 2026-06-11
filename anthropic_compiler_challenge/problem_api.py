"""Stable imports for the frozen challenge problem definition.

The submission environment provides ``frozen_problem``. The fallback keeps local
development working if only ``problem.py`` is available.
"""

try:
    from frozen_problem import (
        DebugInfo,
        SLOT_LIMITS,
        VLEN,
        N_CORES,
        SCRATCH_SIZE,
        Machine,
        Tree,
        Input,
        build_mem_image,
        reference_kernel2,
        reference_kernel,
    )
except ImportError:  # local dev fallback
    from problem import (
        DebugInfo,
        SLOT_LIMITS,
        VLEN,
        N_CORES,
        SCRATCH_SIZE,
        Machine,
        Tree,
        Input,
        build_mem_image,
        reference_kernel2,
        reference_kernel,
    )

__all__ = [
    "DebugInfo",
    "SLOT_LIMITS",
    "VLEN",
    "N_CORES",
    "SCRATCH_SIZE",
    "Machine",
    "Tree",
    "Input",
    "build_mem_image",
    "reference_kernel2",
    "reference_kernel",
]
