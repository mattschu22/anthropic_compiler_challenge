import { addTitle, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Optimization Roadmap: Cumulative Checkpoints");
  addSubtitle(slide, ctx, "These are cumulative checkpoints, not independent ablations.");
  addBullets(slide, ctx, [
    "0 Baseline: 147,734 cycles.",
    "1 Remove index bookkeeping: 114,868 cycles.",
    "2 Specialized fixed layout: 110,898 cycles.",
    "3 Round unrolling: 97,040 cycles.",
    "4 Vectorization: 12,285 cycles.",
    "5 Tree caching: 11,856 cycles.",
    "6 Streaming value I/O: 11,825 cycles.",
    "7 Temporary banks: 8,884 cycles.",
    "8 VLIW scheduling: 1,291 cycles.",
    "9 Final refinements: 1,184 cycles."
  ], 70, 145, 1060, 15, 30);
  addPlaceholder(slide, ctx, "Codebase image: use optimization_ladder/results/charts/optimization_ladder.svg, the 10-rung line chart grouped into phases: remove work, specialize, vectorize/memory, expose work, schedule machine.");
  return slide;
}
