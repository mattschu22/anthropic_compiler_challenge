import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Bottleneck Analysis: Memory Pressure Moves To Hot Tree Nodes");
  addCycleBadge(slide, ctx, "Current: 11,825 cycles");
  addSubtitle(slide, ctx, "After SIMD, remaining gains come from reducing repeated memory work and regularizing I/O.");
  addBullets(slide, ctx, [
    "Stage 5, tree caching: 12,285 -> 11,856 cycles.",
    "Upper tree nodes are reused by many inputs.",
    "The root is touched by every input; reuse roughly halves at each tree depth.",
    "Caching shallow nodes replaces repeated gathers with scratch/vector selects.",
    "Stage 6, streaming value I/O: 11,856 -> 11,825 cycles.",
    "Streaming value I/O makes address generation a compact moving-pointer pattern.",
    "Narrative role: the trace changes the question from 'can I vectorize?' to 'what resource is binding now?'"
  ], 70, 150, 1060, 16, 34);
  addPlaceholder(slide, ctx, "Codebase image + PowerPoint inset: use charts/tree_cache_heatmap.svg or charts/tree_cache_heatmap_rounds.svg for reuse; add scratch-cache inset showing hot nodes moved from repeated LOADs into scratch/vector selects, plus a small streaming-pointer strip for value I/O.");
  return slide;
}
