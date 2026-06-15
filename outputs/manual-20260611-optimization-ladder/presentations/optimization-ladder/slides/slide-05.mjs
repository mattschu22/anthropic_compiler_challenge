import { addTitle, addFooter, bulletList, colors, image, stageMiniTable } from "./common.mjs";

export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Optimization Roadmap: Cumulative Checkpoints", "Each rung preserves correctness and adds one narrative capability.", "roadmap");

  await image(slide, ctx, "charts/optimization_ladder.png", 52, 146, 660, 410, "Optimization ladder");

  stageMiniTable(slide, ctx, [
    ["0 Baseline", "supplied reference point", "147,734", colors.muted],
    ["1 Remove work", "remove index bookkeeping", "114,868", colors.green],
    ["2-3 Specialize", "fixed layout + unroll", "97,040", colors.cyan],
    ["4 SIMD", "8 inputs per vector op", "12,285", colors.violet],
    ["5-6 Memory", "cache hot nodes + stream I/O", "11,825", colors.amber],
    ["7-9 Schedule", "temp banks + VLIW + refinements", "1,184", colors.rose],
  ], 750, 156, 420, 286);

  bulletList(slide, ctx, [
    "The story is chronological: remove unnecessary work first, then unlock hardware parallelism.",
    "The largest drops happen when the program shape changes: scalar to SIMD, then unscheduled to VLIW-packed."
  ], 760, 472, 370, { size: 15, gap: 52, bulletColor: colors.blue });

  addFooter(slide, ctx, 5);
  return slide;
}
