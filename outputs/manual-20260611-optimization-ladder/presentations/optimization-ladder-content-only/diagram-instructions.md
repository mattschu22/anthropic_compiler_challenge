# Diagram Instructions For Content-Only Deck

These instructions are for completing the unstylized content-only deck. The
deck tells a profiler-guided compiler optimization story: start with a correct
but serialized scalar tree-traversal kernel, repeatedly use traces to identify
the current bottleneck, and end with a dense VLIW/SIMD schedule.

Use simple editable PowerPoint shapes wherever possible. Use codebase images
only where called out explicitly. The canonical asset root is:

`/Users/baseb/Documents/Projects/AnthropicPerf/anthropic_compiler_challenge/optimization_ladder/results`

## Shared Stage Context

Presentation stages are cumulative checkpoints, not independent ablations:

| Stage | Name | Cycles | Main idea |
| --- | --- | ---: | --- |
| 0 | Baseline | 147,734 | Correct scalar-ish implementation with heavy bookkeeping and memory traffic. |
| 1 | Remove Index Bookkeeping | 114,868 | Combine test-contract cleanup and scratch-resident indices. |
| 2 | Specialized Fixed Layout | 110,898 | Bake in benchmark memory/layout constants. |
| 3 | Round Unrolling | 97,040 | Emit the known 16-round operation sequence. |
| 4 | Vectorization | 12,285 | Process 256 inputs as 32 groups of 8 SIMD lanes. |
| 5 | Tree Caching | 11,856 | Cache hot upper tree nodes in scratch. |
| 6 | Streaming Value IO | 11,825 | Regularize value memory updates into a compact streaming pattern. |
| 7 | Temporary Banks | 8,884 | Expose independent work by avoiding false dependencies through reused temp names. |
| 8 | VLIW Scheduling | 1,291 | Pack ready operations across ALU, VALU, LOAD, STORE, FLOW slots. |
| 9 | Final Refinements | 1,184 | Relax safe hazards and use VALU-to-ALU fallback where profitable. |

## Slide 1: Hero Metric

Diagram type: PowerPoint diagram.

Purpose: Open with the result and the idea that this was a systematic ladder,
not a single trick.

Build instructions:
- Create a large left-to-right metric arrow: `147,734 cycles` -> `1,184 cycles`.
- Add a prominent `124.8x faster` callout above or below the arrow.
- Add a small 10-rung sparkline below the metric using the stage sequence above.
- Mark the two largest drops: stage 4 `Vectorization` and stage 8 `VLIW scheduling`.
- Keep the diagram readable at thumbnail size; this is the first visual thesis.

## Slide 3: Batched Binary Tree Traversal

Diagram type: PowerPoint diagram.

Purpose: Explain the computation before discussing optimizations.

Context:
- Workload constants: `forest_height = 10`, `rounds = 16`, `batch_size = 256`.
- Each input has a current `value` and current tree `index`.
- One round reads a tree node, mixes it with the current value through a hash,
  computes a branch bit, updates the value, and moves to the next tree index.
- Depths follow `0,1,2,3,4,5,6,7,8,9,10,0,1,2,3,4`.
- Correctness target: final values must match the reference implementation.

Build instructions:
- Left side: draw a compact perfect binary tree labeled depth 0 through depth 10.
- Highlight one path from root to leaf with arrows.
- Right side: draw one-round dataflow:
  `value + index` -> `node lookup` -> `hash/mix` -> `branch bit` -> `next index + next value`.
- Add a batch label showing that the same logic is applied to 256 independent inputs.
- Do not overdraw all 2,047 nodes; show the concept with a collapsed lower tree.

## Slide 4: Machine Model And Perfetto Tooling

Diagram type: PowerPoint diagram.

Purpose: Teach how to read later performance visuals.

Context:
- The simulated machine issues one VLIW packet per cycle.
- Per cycle capacity is `12 ALU`, `6 VALU`, `2 LOAD`, `2 STORE`, `1 FLOW`.
- SIMD vector width is 8.
- ALU handles scalar arithmetic/comparisons/address math.
- VALU handles vector arithmetic across 8 lanes.
- LOAD/STORE handle memory reads/writes.
- FLOW handles control operations.
- Perfetto-style traces show engine activity over time; dense bars mean busy
  slots, blank gaps indicate idle capacity or dependency bubbles.

Build instructions:
- Draw one horizontal "cycle packet" row split into five engine groups:
  12 ALU boxes, 6 VALU boxes, 2 LOAD boxes, 2 STORE boxes, 1 FLOW box.
- Use distinct colors for each engine and reuse the same colors later.
- Add a small legend explaining "slot filled = issued operation".
- Add a small trace strip underneath as supporting evidence, but keep the issue
  packet as the main teaching object.

## Slide 5: Optimization Roadmap

Diagram type: Codebase image with light PowerPoint annotation.

Asset: `charts/optimization_ladder.png`.

Purpose: Give the audience a map of the story before entering individual steps.

Context:
- The line chart uses the merged presentation stages `0` through `9`.
- The narrative phases are: remove work, specialize, vectorize/memory, expose
  independent work, schedule the machine.
- The two major inflections are stage 4 vectorization and stage 8 VLIW scheduling.

Build instructions:
- Place `charts/optimization_ladder.png` as the main visual.
- Add phase bands or labels along the x-axis:
  `remove work`, `specialize`, `vectorize + memory`, `expose work`, `schedule`.
- Add callouts on stage 4 and stage 8 with cycle deltas:
  `97,040 -> 12,285` and `8,884 -> 1,291`.
- Avoid turning this into a bar chart; the deck narrative is cumulative progress.

## Slide 6: Baseline Trace Reading

Diagram type: Codebase image plus PowerPoint callouts.

Asset: `trace_visuals/00_baseline.png`.

Purpose: Make Perfetto interpretation credible before using traces as evidence.

Context:
- Baseline cycle count is `147,734`.
- Baseline is correct but serialized.
- Most work is scalar execution, index bookkeeping, loop/control overhead, and
  memory traffic.
- VALU lanes are mostly idle because the code has not yet batched inputs into
  vector groups.

Build instructions:
- Place `trace_visuals/00_baseline.png` as the main image.
- Add four callouts:
  `scalar lane activity`, `idle VALU capacity`, `index memory traffic`, and
  `dependency/control bubbles`.
- Use arrows to point at sparse activity and blank regions in the trace.
- Add a small caption: "The first goal is to remove bookkeeping and memory
  traffic before deep scheduling."

## Slide 7: Remove Index Bookkeeping

Diagram type: PowerPoint before/after state diagram.

Purpose: Explain the combined first presentation rung.

Context:
- This presentation stage combines two raw checkpoints: exploiting the test
  contract and moving indices out of memory.
- Cycle improvement: `147,734 -> 114,868`.
- The grader checks final values, not final indices.
- Traversal indices are still needed during execution, but they can live in
  scratch state instead of being loaded/stored through memory every round.

Build instructions:
- Left "before" lane:
  `load index from memory` -> `compute next index` -> `store index to memory`
  repeated per round, plus a final index write.
- Right "after" lane:
  `scratch index` -> `compute next index` -> `scratch index`, with the final
  index write crossed out.
- Add the delta badge `147,734 -> 114,868 cycles`.
- Label this as "remove ungraded work + keep live state close to compute".

## Slide 8: Specialization And Unrolling

Diagram type: PowerPoint comparison diagram.

Purpose: Show why fixed benchmark knowledge lets the compiler emit simpler code.

Context:
- Stage 2: fixed layout, `114,868 -> 110,898`.
- Stage 3: unrolling, `110,898 -> 97,040`.
- The challenge workload is stable: fixed forest height, fixed 16 rounds, fixed
  batch size, and stable memory layout.
- Instruction file size grows, but the score is simulator cycles.

Build instructions:
- Left side: generic loop block with labels:
  `read layout`, `check depth`, `loop branch`, `compute`.
- Right side: fixed 16-step strip labeled:
  `0,1,2,3,4,5,6,7,8,9,10,0,1,2,3,4`.
- Show baked-in pointer/layout constants feeding the right strip.
- Include two small delta labels for fixed layout and unrolling.
- Make clear that this is still mostly scalar; vectorization has not happened yet.

## Slide 9: SIMD Batching

Diagram type: PowerPoint diagram.

Purpose: Explain the first large structural speedup.

Context:
- Stage 4 cycle improvement: `97,040 -> 12,285`.
- SIMD vector width is 8.
- `256 inputs / 8 lanes = 32 vector groups`.
- The hash pipeline, value update, branch-bit calculation, and many index
  updates become lane-wise vector operations.

Build instructions:
- Draw eight separate scalar input tokens collapsing into one 8-lane vector.
- Label the lanes `lane 0` through `lane 7`.
- Show 32 vector groups as a compact stack or grid.
- Add a vector operation block applied across all lanes:
  `hash`, `value update`, `branch bit`, `index update`.
- Include a small note: "This is where the trace shifts toward VALU as the main engine."

## Slide 10: Tree Caching And Streaming Value IO

Diagram type: Codebase image plus PowerPoint insets.

Primary asset: `charts/tree_cache_heatmap_rounds.png`.
Optional supporting asset: `charts/tree_cache_heatmap.png`.

Purpose: Explain the memory-pressure stage after vectorization.

Context:
- Stage 5 tree caching: `12,285 -> 11,856`.
- Stage 6 streaming value I/O: `11,856 -> 11,825`.
- In a tree, the root is visited by every input; reuse halves each depth.
- Stage 5 caches the 7 hottest nodes, depths 0 through 2, which is only 0.34%
  of the full 2,047-node tree.
- Because the 16-round sequence revisits shallow depths, depths 0 through 4 are
  weighted more heavily in the polished heatmap.
- Streaming value I/O regularizes address updates into a moving-pointer pattern.

Build instructions:
- Place `charts/tree_cache_heatmap_rounds.png` as the main visual.
- Add an inset showing hot upper nodes moving from `LOAD each time` to
  `scratch cache` / `vector select`.
- Add a second small strip for streaming value I/O:
  before = scattered address recomputation; after = `base pointer + stride`.
- Label the stage as a modest but important bottleneck transition, not a huge
  headline gain.

## Slide 11: Temporary Banks

Diagram type: PowerPoint false-dependency before/after.

Purpose: Show that independent work must be visible to the scheduler.

Context:
- Stage 7 cycle improvement: `11,825 -> 8,884`.
- A fully unrolled vector program has many logically independent vector groups.
- If unrelated groups reuse the same temporary scratch names, dependency
  analysis treats them as serialized.
- Temporary banks give independent groups separate names, increasing the number
  of ready operations.
- This is preparation for the full global VLIW scheduler, not the scheduler itself.

Build instructions:
- Left side: three independent vector groups all writing/reading the same temp
  names, causing a red "false dependency" chain.
- Right side: the same groups assigned to `temp bank A`, `temp bank B`,
  `temp bank C`, allowing parallel ready queues.
- Add a short caption: "Rename temps to expose independence."
- Show the cycle delta `11,825 -> 8,884`.

## Slide 12: Dependency-Aware VLIW Scheduler

Diagram type: PowerPoint diagram plus small codebase image inset.

Inset asset: `trace_visuals/09_final_refinements.png`.

Purpose: Explain the final major speedup in a way that feels rigorous.

Context:
- Stage 8 VLIW scheduling: `8,884 -> 1,291`.
- Stage 9 final refinements: `1,291 -> 1,184`.
- Each logical operation has an engine type and explicit read/write sets.
- RAW hazard: a consumer reads after a producer writes.
- WAW hazard: two writes to the same target must preserve order.
- WAR hazard: a later write must not clobber an earlier read.
- Final refinements relax safe same-cycle WAR cases because reads happen at
  cycle start and writes commit at cycle end.
- Ready operations are prioritized by critical path and packed under engine slot limits.

Build instructions:
- Left: small dependency DAG with nodes colored by engine type.
- Label example edges `RAW`, `WAR`, `WAW`.
- Middle: ready queue ordered by critical path.
- Right: one or two VLIW packet rows with slots:
  `12 ALU`, `6 VALU`, `2 LOAD`, `2 STORE`, `1 FLOW`.
- Add the small inset `trace_visuals/09_final_refinements.png` only as proof of
  dense utilization; the dependency model should be the main visual.
- Add both cycle deltas: `8,884 -> 1,291` and `1,291 -> 1,184`.

## Slide 13: Results And Bottleneck Movement

Diagram type: Codebase chart combination.

Primary assets:
- `charts/optimization_ladder.png`
- `charts/utilization_ladder.png`

Optional assets:
- `charts/issue_density.png`
- `charts/shifting_bottleneck.png`

Purpose: Summarize that the binding constraint changed over time.

Context:
- Early gains remove wasted bookkeeping and memory traffic.
- Middle gains specialize fixed workload shape and vectorize across the batch.
- Late gains are scheduling improvements, not major reductions in logical work.
- The optimization ladder is useful because it shows how profiler interpretation
  drove each step.

Build instructions:
- Use `charts/optimization_ladder.png` as the main chart.
- Add `charts/utilization_ladder.png` or `charts/issue_density.png` underneath
  or to the side to explain why cycles dropped.
- Annotate two inflection points: `SIMD` and `VLIW scheduling`.
- Add a small "bottleneck moved" row:
  `serialization` -> `memory pressure` -> `exposed independence` -> `scheduling`.

## Slide 15: Next Steps Pipeline

Diagram type: PowerPoint roadmap diagram.

Purpose: Turn the project into a compiler-engineering roadmap.

Context:
- Current work is a specialized hand-built kernel optimization ladder.
- Next steps should generalize the approach: better profiling metrics,
  dependency modeling, scratch/register allocation, and scheduler search.
- The final next step is a formal dependency model: represent every instruction
  as a graph node with explicit reads, writes, engine constraints, and
  RAW/WAR/WAW edges; use the graph to prove schedule correctness and search for
  better VLIW packing.

Build instructions:
- Draw a left-to-right compiler pipeline:
  `trace metrics` -> `dependency graph` -> `register coloring` ->
  `scheduler search` -> `verified VLIW program`.
- Add feedback arrows from `trace metrics` back to `scheduler search`.
- Put the dependency graph in the center as the anchor, since it supports
  both correctness and scheduling quality.
- Use small sublabels:
  `goodput`, `hazards`, `liveness`, `engine slots`, `verification`.
