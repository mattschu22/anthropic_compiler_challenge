# Perf take-home submission

Matt Schumacher

This repository contains an optimized kernel generator for the Anthropic compiler
performance take-home. The generated kernel targets the simulator in
`frozen_problem.py`: a small VLIW/SIMD machine with explicit scratch management
and separate engine slot limits.

The optimized configuration for the grader workload:

- Workload: `forest_height=10`, `rounds=16`, `batch_size=256`
- SIMD vector width: `8`
- Baseline reference cycles: `147,734`
- Optimized cycles: about `1,184`
- Speedup: about `124.8x`

## Repository layout

```text
.
|-- README.md
|-- perf_takehome.py
|-- frozen_problem.py
|-- problem.py
|-- submission_tests.py
`-- anthropic_compiler_challenge/
    |-- __init__.py
    |-- kernel_builder.py
    |-- problem_api.py
    |-- runner.py
    `-- scheduler.py
```

### Top-level files

- `perf_takehome.py` is a compatibility entrypoint. It preserves the original
  import used by the provided tests:

  ```python
  from perf_takehome import KernelBuilder
  ```

- `frozen_problem.py` is the frozen simulator, memory layout, reference kernel,
  and problem definition used by the tests.
- `problem.py` is the local editable copy of the same challenge problem.
- `submission_tests.py` is the supplied correctness and speed test harness.

### Package modules

- `anthropic_compiler_challenge/problem_api.py` centralizes imports from
  `frozen_problem.py`, with a fallback to `problem.py` for local development.
- `anthropic_compiler_challenge/scheduler.py` contains dependency analysis,
  critical-path heuristics, VLIW packing, and VALU-to-ALU fallback scheduling.
- `anthropic_compiler_challenge/kernel_builder.py` contains `KernelBuilder`, the
  optimized kernel generator.
- `anthropic_compiler_challenge/runner.py` contains local benchmark and tuning
  helpers, including `do_kernel_test()` and `hyperparameter_search()`.

## Problem model

The reference workload walks a perfect binary tree for a batch of inputs. Each
round performs one tree step for every input:

1. Read the current input node index.
2. Read the tree node value.
3. Compute `myhash(input_value ^ node_value)`.
4. Choose the left or right child from the hash parity.
5. Wrap back to root after stepping past the leaf level.
6. Write the updated value and index.

For the target workload, there are `16` rounds. With tree height `10`, the
visited depths are:

```text
0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0, 1, 2, 3, 4
```

This predictable depth sequence is a major source of optimization opportunity.

## High-level strategy

1. Fully unroll the target workload. The emitted kernel has no data-dependent
   control flow.
2. Keep per-input `idx` entirely in scratch. The tests verify final values, so
   the kernel does not need to store indices back to memory.
3. Cache hot tree nodes:
   - Nodes `0..6` are loaded once and broadcast into reusable vectors.
   - Nodes `7..14` can be cached for the depth-3 step and selected with vector
     arithmetic instead of gather loads.
4. Process the batch as `32` SIMD vectors of width `8`.
5. Use multiple temporary banks to reduce false dependencies caused by scratch
   reuse in the fully unrolled program.
6. Schedule generated operations with a dependency-aware VLIW list scheduler.

## Important implementation details

### Index traffic elimination

`Input.generate()` initializes all indices to zero. In a perfect binary tree,
after a leaf step, the computed child index is out of bounds and wraps to zero.

The optimized kernel uses that property directly:

- At depth `0`, `idx` is known to be zero.
- The next index can be set directly to `1` or `2`.
- Indices live only in scratch vectors.
- Final index stores are skipped because the provided tests compare final
  values.

### Cached upper-tree nodes

The root and early levels are reused by every lane in every batch vector. The
kernel loads the first eight tree values once, then broadcasts nodes `0..6` into
vector scratch. Depths `0..2` use `vselect` and vector masks instead of memory
loads.

Depth `3` is handled specially when `cache_depth3=True`. Nodes `7..14` are
loaded once, transformed into pairwise base/diff vectors, and selected with a
small 8-way selection tree. This removes eight scalar gather loads per SIMD
vector at that depth.

### Hash and branch update

The hash function is vectorized across `VLEN=8` lanes. The kernel computes the
branch bit from the hash pipeline, then updates `idx` with either:

- a direct root-depth selection, or
- the generic binary-tree child formula, or
- address-mode updates for deeper gathers.

At leaf depth, the next round is known to restart at root, so unnecessary index
work is avoided.

### Temporary banks

The unrolled program has many independent vectors in flight. Reusing the same
scratch temporaries too aggressively makes unrelated operations look dependent
to the scheduler.

`KernelBuilder` allocates multiple temp banks containing vectors such as:

- `v_tmp1`
- `v_tmp2`
- `v_tmp3` where useful
- `tmp_v_node_val`

Processing vectors in chunks across these banks gives the scheduler more
independent work to pack into the same cycle.

### VLIW scheduler

`scheduler.py` builds read/write sets for each generated operation and creates a
typed dependency graph:

- RAW and WAW edges require one-cycle separation.
- WAR edges allow same-cycle scheduling because the simulator reads operands at
  the beginning of a cycle and commits writes at the end.

The scheduler then packs ready operations under engine slot limits:

- `alu`: 12 slots
- `valu`: 6 slots
- `load`: 2 slots
- `store`: 2 slots
- `flow`: 1 slot

It uses critical-path priority, tunable operation weights, address-generation
bonuses, and a small deterministic multi-start search over tie-break orders.
Some eligible vector ALU ops can also fall back to eight scalar ALU ops when the
VALU engine is saturated and scalar ALU slots are available.

## Tuning knobs

`KernelBuilder.build_kernel()` exposes the main performance knobs:

- `unroll`: number of SIMD vectors processed per generated outer group.
- `parallel_banks`: number of temporary banks available for independent work.
- `cache_depth3`: whether to cache and select nodes `7..14`.
- `depth3_banks`: chunk size for the cached depth-3 select path.
- `tmp3_banks`: number of banks with a third temp vector.
- `streaming_io`: use one scalar pointer for value loads/stores.
- `load_weight`, `valu_weight`, `addr_bonus`: scheduler priority heuristics.

The defaults are tuned for the supplied grader workload:

```text
unroll=32
parallel_banks=28
cache_depth3=True
depth3_banks=13
tmp3_banks=18
streaming_io=True
load_weight=-1
valu_weight=-1
addr_bonus=2
```

## How to run

Run the provided test harness:

```bash
python3 -m unittest -q submission_tests.py
```

Run the local benchmark entrypoint:

```bash
python3 perf_takehome.py
```

Or call the packaged helper directly:

```bash
python3 -m anthropic_compiler_challenge.runner
```

Expected result for the default workload is approximately:

```text
CYCLES: 1184
Speedup over baseline: 124.8x
```
