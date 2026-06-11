# Slide Asset Map

Use the line chart as the recurring navigation visual, then pair each checkpoint
slide with its trace visual and the interpretation below.

| Stage | Checkpoint | Trace visual | Interpretation |
| --- | --- | --- | --- |
| 0 | Baseline | `trace_visuals/00_baseline.svg` | Scalar execution leaves most machine lanes idle. |
| 1 | Exploit Test Contract | `trace_visuals/01_test_contract.svg` | Final value-only pass removes useless final index work. |
| 2 | Move Indices Out Of Memory | `trace_visuals/02_scratch_indices.svg` | Index state is no longer memory traffic; remaining work is compute-heavy. |
| 3 | Specialized Fixed Layout | `trace_visuals/03_fixed_layout.svg` | Header/pointer setup shrinks, but execution shape is still scalar. |
| 4 | Round Unrolling | `trace_visuals/04_unroll.svg` | Control overhead is gone; fixed depth sequence is now visible. |
| 5 | Vectorization | `trace_visuals/05_vectorize.svg` | VALU lanes become the main workhorse after batching eight inputs. |
| 6 | Tree Caching | `trace_visuals/06_tree_cache.svg` | Load activity drops for shallow depths because hot tree nodes live in scratch. |
| 7 | Streaming Value IO | `trace_visuals/07_streaming_io.svg` | Address work becomes a compact streaming pattern. |
| 8 | Temporary Banks | `trace_visuals/08_temp_banks.svg` | Independent work is exposed and locally packed before global scheduling. |
| 9 | VLIW Scheduling | `trace_visuals/09_vliw_schedule.svg` | Cross-engine scheduling fills many lanes in the same cycle. |
| 10 | Final Refinements | `trace_visuals/10_final_refinements.svg` | Relaxed hazards and VALU-to-ALU fallback squeeze the last cycles out. |

Primary charts:

- `charts/optimization_ladder.svg` — cycles vs. checkpoint (the "what": steady
  cycle reduction, with SIMD and VLIW called out as the two big drops).
- `charts/utilization_ladder.svg` — per-engine busy fraction vs. checkpoint (the
  "why": VALU switches on at stage 5, every engine fills at stage 9). Pair this
  immediately after the cycle chart to connect each drop to the machine state
  that caused it.

Bottleneck charts (the "what was limiting each rung" story — the binding
constraint moves: serialization → memory → scheduling → VALU throughput):

- `charts/shifting_bottleneck.svg` — named binding constraint per rung. Best as
  the framing/capstone slide for the bottleneck discussion.
- `charts/issue_density.svg` — ops/cycle per stage vs. the 23-slot peak; the gap
  above each bar is idle machine (4% → 86% full).
- `charts/work_vs_time.svg` — total ops issued vs. cycles; ops go flat after
  vectorize while cycles keep falling, proving the back half is pure scheduling.
- `charts/op_composition.svg` — share of issued ops by engine per stage; shows
  which engine dominates the work mix as the bottleneck moves.

Stage deep-dives:

- `charts/tree_cache_heatmap.svg` — reuse heat-mapped onto the depth-10 tree.
  Every input passes through the root, so a node at depth d is traversed by
  256/2^d inputs; reuse halves each level. Stage 6 caches the 7 hottest nodes
  (depths 0–2) — 0.34% of the tree — turning the most-reused gathers into vector
  selects. Use as the stage-6 "why it works" slide.
- `charts/tree_cache_heatmap_rounds.svg` — polished stage-6 diagram: heat
  weighted by the real 16-round schedule (depths 0–4 traversed twice, marked
  ×2). Depths 0–4 are drawn as an explicit heat-labeled binary tree; depths
  5–10 are collapsed into cold heat-graded subtree wedges (2,016 nodes, reuse
  ≤ 8×). The clean "hot crown over cold base" framing for the stage-6 slide.

Full Perfetto-compatible traces:

- `traces/00_baseline.json`
- `traces/01_test_contract.json`
- `traces/02_scratch_indices.json`
- `traces/03_fixed_layout.json`
- `traces/04_unroll.json`
- `traces/05_vectorize.json`
- `traces/06_tree_cache.json`
- `traces/07_streaming_io.json`
- `traces/08_temp_banks.json`
- `traces/09_vliw_schedule.json`
- `traces/10_final_refinements.json`
