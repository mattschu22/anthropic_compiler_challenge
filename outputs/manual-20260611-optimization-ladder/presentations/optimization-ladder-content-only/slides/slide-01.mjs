import { addTitle, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Profiler-Guided Compiler Optimization");
  addSubtitle(slide, ctx, "Anthropic compiler performance take-home: from scalar tree traversal to scheduled VLIW/SIMD kernel");
  addBullets(slide, ctx, [
    "Project result: 147,734 cycles to 1,184 cycles on the fixed grader workload.",
    "Final speedup: approximately 124.8x over the supplied baseline.",
    "Thesis: remove unnecessary work, specialize the workload, exploit SIMD, reduce memory pressure, expose independent work, and schedule that work onto the machine.",
    "The presentation is trace-backed: every major optimization is tied to what the profiler showed."
  ]);
  addPlaceholder(slide, ctx, "PowerPoint diagram: hero metric visual with large 147,734 cycles -> 1,184 cycles arrow, 124.8x speedup callout, and a tiny 10-rung ladder sparkline.");
  return slide;
}
