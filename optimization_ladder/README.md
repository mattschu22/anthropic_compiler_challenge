# Optimization Ladder

This directory contains runnable cumulative checkpoints for the SpaceX interview
performance narrative. These are not independent ablations. Each checkpoint is a
rung in the path from the reference workload to the final tuned kernel.

## Checkpoints

| Stage | ID | Claim |
| --- | --- | --- |
| 0 | `00_baseline` | Supplied benchmark baseline. |
| 1 | `01_test_contract` | Final index writes are not graded. |
| 2 | `02_scratch_indices` | Keep live index state in scratch. |
| 3 | `03_fixed_layout` | Bake in stable workload and memory layout. |
| 4 | `04_unroll` | Expose the deterministic round/depth sequence. |
| 5 | `05_vectorize` | Process eight inputs per vector instruction. |
| 6 | `06_tree_cache` | Cache high-reuse upper tree nodes. |
| 7 | `07_streaming_io` | Stream value addresses through one moving pointer. |
| 8 | `08_temp_banks` | Add independent temp banks for later scheduling. |
| 9 | `09_vliw_schedule` | Pack work into VLIW engine slots. |
| 10 | `10_final_refinements` | Use the final relaxed scheduler and tuned priorities. |

## Run

Run one checkpoint:

```bash
python3 -m optimization_ladder.runner 05_vectorize --no-csv
```

Run every checkpoint and write `results/cycles.csv`:

```bash
python3 -m optimization_ladder.runner --all
```

Generate the marked line-chart SVG from the latest CSV:

```bash
python3 -m optimization_ladder.chart
```

Generate compact Perfetto-style lane visuals for each checkpoint:

```bash
python3 -m optimization_ladder.trace_visuals
```

Capture Perfetto-compatible traces for every checkpoint:

```bash
python3 -m optimization_ladder.runner --all --trace all
```

The trace files are written under `optimization_ladder/results/traces/`.
The reported baseline is not an emitted machine program, so `00_baseline.json`
uses an equivalent scalar machine kernel for the trace while preserving the
supplied `147,734` cycle number in `results/cycles.csv`.

Slide-ready trace SVGs are written under
`optimization_ladder/results/trace_visuals/`. These are derived from the same
trace JSON files and are intended for direct use in the deck when a full
Perfetto screenshot would be too dense.

## Presentation Notes

Stage 8 uses temp banks plus local same-engine slot packing. It does not run the
global VLIW scheduler; stage 9 is still the first checkpoint that performs
dependency-aware cross-engine scheduling.

Stage 1 is intentionally modest. The test contract only makes final index state
irrelevant after the last value has already been computed. See
`results/test_contract_analysis.md`.
