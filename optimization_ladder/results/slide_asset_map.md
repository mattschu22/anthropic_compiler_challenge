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

Primary chart:

- `charts/optimization_ladder.svg`

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
