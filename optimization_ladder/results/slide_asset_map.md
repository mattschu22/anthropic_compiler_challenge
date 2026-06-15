# Slide Asset Map

Use the line chart as the recurring navigation visual, then pair each checkpoint
slide with its trace visual and the interpretation below.

| Stage | Checkpoint | Trace visual | Interpretation |
| --- | --- | --- | --- |
| 0 | Baseline | `trace_visuals/00_baseline.png` | Scalar execution leaves most machine lanes idle. |
| 1 | Removing Unnecessary Work | `trace_visuals/01_remove_unnecessary_work.png` | Final index work is skipped and live indices stay in scratch instead of memory. |
| 2 | Specialize For The Workload | `trace_visuals/02_specialize_workload.png` | Fixed layout and the deterministic round/depth sequence remove generic control work. |
| 3 | Vectorize | `trace_visuals/03_vectorize.png` | VALU lanes become the main workhorse after batching eight inputs and streaming value IO. |
| 4 | Schedule RAW/WAR/WAW Dependencies | `trace_visuals/04_schedule_dependencies.png` | Dependency-aware scheduling helps, but reused temporaries create false dependencies. |
| 5 | Virtualize Temporaries Through Banks | `trace_visuals/05_temp_banks.png` | Independent vector groups get separate temp banks, exposing parallel work to the scheduler. |
| 6 | Implement Tree Caching | `trace_visuals/06_tree_cache.png` | Load activity drops for shallow depths because hot tree nodes live in scratch. |
| 7 | Tune The Scheduler | `trace_visuals/07_scheduler_tuning.png` | Relaxed hazards and tuned priorities squeeze the last cycles out. |

Source code:

- `charts/code_reference_kernel.png` — the original `reference_kernel` source,
  syntax-highlighted. Use as the "here's the workload" slide.
- `charts/code_reference_kernel_index_removed.png` — same source with the index
  memory load/writeback struck through. Use on the "Removing Unnecessary Work"
  rung to show exactly what left memory (index stays in scratch; final indices
  aren't graded).
- `charts/unroll_diagram.png` — rolled generic loop (runtime depth %, header
  layout load, per-round branch) vs. the unrolled 16-step schedule with the
  fixed depth sequence (0–10, 0–4) and baked-in layout constants. Use on the
  "Specialize For The Workload" rung.
- `charts/scheduler_diagram.png` — RAW/WAR/WAW data-dependency graph with the
  critical path (longest RAW chain) highlighted, showing the cycle floor. Only
  RAW extends the critical path; WAR/WAW also constrain ordering. Use on the
  "Schedule RAW/WAR/WAW Dependencies" rung.

Machine overview:

- `charts/cpu_diagram.png` — the target VLIW + SIMD core: per-engine slot counts
  (ALU 12, VALU 6, LOAD/STORE 2, FLOW 1 = 23 issue slots/cycle), the 8-wide SIMD
  lanes, and each engine's instruction set. Use as the architecture/setup slide
  so later "fill the engines" and "VLIW packing" claims have a referent.

Primary charts:

- `charts/optimization_ladder.png` — cycles vs. checkpoint (the "what": steady
  cycle reduction, with SIMD and temp banking called out as the two big drops).
- `charts/utilization_ladder.png` — per-engine busy fraction vs. checkpoint (the
  "why": VALU switches on at stage 3, every engine fills after temp banking).
  Pair this immediately after the cycle chart to connect each drop to the
  machine state that caused it.

Bottleneck charts (the "what was limiting each rung" story — the binding
constraint moves: serialization → vectorization → false dependencies → VALU
throughput):

- `charts/shifting_bottleneck.png` — named binding constraint per rung. Best as
  the framing/capstone slide for the bottleneck discussion.
- `charts/issue_density.png` — ops/cycle per stage vs. the 23-slot peak; the gap
  above each bar is idle machine.
- `charts/work_vs_time.png` — total ops issued vs. cycles; ops go flat after
  vectorize while cycles keep falling, proving the back half is pure scheduling.
- `charts/op_composition.png` — share of issued ops by engine per stage; shows
  which engine dominates the work mix as the bottleneck moves.

Stage deep-dives:

- `charts/tree_cache_heatmap.png` — reuse heat-mapped onto the depth-10 tree.
  Every input passes through the root, so a node at depth d is traversed by
  256/2^d inputs; reuse halves each level. Stage 6 caches the hottest upper nodes
  (depths 0–2) — 0.34% of the tree — turning the most-reused gathers into vector
  selects. Use as the stage-6 "why it works" slide.
- `charts/tree_cache_heatmap_rounds.png` — polished stage-6 diagram: heat
  weighted by the real 16-round schedule (depths 0–4 traversed twice, marked
  ×2). Depths 0–4 are drawn as an explicit heat-labeled binary tree; depths
  5–10 are collapsed into cold heat-graded subtree wedges (2,016 nodes, reuse
  ≤ 8×). The clean "hot crown over cold base" framing for the stage-5 slide.

Full Perfetto-compatible traces:

- `traces/00_baseline.json`
- `traces/01_remove_unnecessary_work.json`
- `traces/02_specialize_workload.json`
- `traces/03_vectorize.json`
- `traces/04_schedule_dependencies.json`
- `traces/05_temp_banks.json`
- `traces/06_tree_cache.json`
- `traces/07_scheduler_tuning.json`
