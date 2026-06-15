import { addTitle, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide13(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Results: The Binding Constraint Moved Over Time");
  addSubtitle(slide, ctx, "The strongest story is not one trick; it is a sequence of bottlenecks found and removed.");
  addBullets(slide, ctx, [
    "Final result: 1,184 cycles.",
    "Final speedup: approximately 124.8x over the 147,734-cycle baseline.",
    "Early gains came from removing unneeded bookkeeping and memory traffic.",
    "Middle gains came from specializing the fixed workload and vectorizing across the batch.",
    "Late gains came from exposing independent work and scheduling it across the VLIW engines.",
    "The optimization ladder is useful because it shows how profiler interpretation evolved as each bottleneck moved."
  ]);
  addPlaceholder(slide, ctx, "Codebase images: use charts/optimization_ladder.svg plus charts/utilization_ladder.svg or charts/issue_density.svg; annotate the two major inflections: SIMD and VLIW scheduling.");
  return slide;
}
