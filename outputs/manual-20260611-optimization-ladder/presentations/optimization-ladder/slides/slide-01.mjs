import { addTitle, addFooter, bulletList, colors, image, metric } from "./common.mjs";

export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Profiler-Guided Compiler Optimization", "Anthropic compiler performance take-home: from scalar tree traversal to scheduled VLIW/SIMD kernel", "title");

  metric(slide, ctx, "147,734 -> 1,184", "cycles on the fixed grader workload", 54, 158, 300, 110, colors.blue);
  metric(slide, ctx, "124.8x", "speedup over supplied baseline", 374, 158, 230, 110, colors.green);
  metric(slide, ctx, "11", "cumulative checkpoints in the optimization ladder", 624, 158, 260, 110, colors.violet);

  bulletList(slide, ctx, [
    "Narrative: remove waste, specialize the workload, exploit SIMD, reduce memory pressure, then schedule independent work.",
    "The key deliverable is not just a fast kernel; it is a trace-backed explanation of why each optimization matters.",
  ], 64, 302, 660, { size: 18, gap: 54 });

  await image(slide, ctx, "charts/optimization_ladder.png", 740, 300, 470, 300, "Optimization ladder chart");
  addFooter(slide, ctx, 1);
  return slide;
}
