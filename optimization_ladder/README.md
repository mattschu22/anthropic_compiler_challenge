# Optimization Ladder

This directory contains runnable cumulative checkpoints for the SpaceX interview
performance narrative. These are not independent ablations. Each checkpoint is a
rung in the path from the reference workload to the final tuned kernel.

## Checkpoints

| Stage | ID | Claim |
| --- | --- | --- |
| 0 | `00_baseline` | Supplied benchmark baseline. |
| 1 | `01_remove_unnecessary_work` | Skip ungraded final index work and keep live indices in scratch. |
| 2 | `02_specialize_workload` | Bake in stable workload, memory layout, and the fixed round/depth sequence. |
| 3 | `03_vectorize` | Process eight inputs per vector instruction and stream value IO. |
| 4 | `04_schedule_dependencies` | Schedule RAW/WAR/WAW dependencies; improvement is limited by false temp dependencies. |
| 5 | `05_temp_banks` | Virtualize temporaries through independent banks so the scheduler sees parallel work. |
| 6 | `06_tree_cache` | Cache high-reuse upper tree nodes. |
| 7 | `07_scheduler_tuning` | Use the final relaxed scheduler and tuned priorities. |

## Run

Run one checkpoint:

```bash
python3 -m optimization_ladder.runner 03_vectorize --no-csv
```

Run every checkpoint and write `results/cycles.csv`:

```bash
python3 -m optimization_ladder.runner --all
```

Generate the marked line-chart SVG from the latest CSV:

```bash
python3 -m optimization_ladder.chart
```

Generate the companion per-engine utilization chart (the "why cycles fell"
view) from the same traces:

```bash
python3 -m optimization_ladder.utilization_chart
```

Generate the four bottleneck charts (issue density vs. peak, the shifting
bottleneck band, work vs. time, and per-stage op composition):

```bash
python3 -m optimization_ladder.bottleneck_charts
```

Generate the stage-6 deep-dive heatmap (reuse mapped onto the depth-10 tree,
explaining why caching the top levels works):

```bash
python3 -m optimization_ladder.tree_cache_heatmap
```

The companion `tree_cache_heatmap_rounds` weights the heat by the real 16-round
schedule (depths 0–4 are traversed twice), exposing the 4× drop between depth 4
and depth 5:

```bash
python3 -m optimization_ladder.tree_cache_heatmap_rounds
```

Generate the target-machine diagram (engine slot counts + per-engine ISA,
straight from `frozen_problem.py`):

```bash
python3 -m optimization_ladder.cpu_diagram
```

Generate the reference-kernel source images (plain, and with the removed index
bookkeeping highlighted):

```bash
python3 -m optimization_ladder.source_image
```

Generate the round-unrolling diagram (rolled generic loop vs. the unrolled
16-step fixed depth schedule + baked-in layout):

```bash
python3 -m optimization_ladder.unroll_diagram
```

Generate the VLIW scheduler diagram (RAW/WAR/WAW dependency graph feeding a
packed cycles-x-engines table, with the critical path highlighted):

```bash
python3 -m optimization_ladder.scheduler_diagram
```

Rasterize every generated chart/trace SVG to PNG (2x) for the slide deck. The
presentation embeds the PNGs, which render consistently across PowerPoint,
Keynote, and Google Slides. Run this after regenerating any chart:

```bash
python3 -m optimization_ladder.to_png
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

The raw trace format intentionally matches the original take-home simulator and
watcher exactly. For the original hot-reload workflow, copy or symlink any
checkpoint trace to `trace.json`, then run:

```bash
python3 watch_trace.py
```

The bundled `watch_trace.py` and `watch_trace.html` are byte-for-byte identical
to the original take-home files.

Slide-ready trace SVGs are written under
`optimization_ladder/results/trace_visuals/`. These are derived from the same
trace JSON files and are intended for direct use in the deck when a full
Perfetto screenshot would be too dense.

## Presentation Notes

Stage 4 intentionally uses a single temporary namespace. The dependency-aware
scheduler can still pack some independent work, but false WAR/WAW dependencies
through reused temporaries keep the improvement moderate.

Stage 5 uses the same scheduled vector shape with multiple temporary banks. This
is the checkpoint that shows why temporary virtualization matters before final
scheduler tuning.
