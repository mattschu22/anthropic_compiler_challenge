import { addTitle, addFooter, bulletList, colors, image, metric } from "./common.mjs";

export async function slide13(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Results: The Binding Constraint Moved Over Time", "The strongest story is not one trick; it is a sequence of bottlenecks found and removed.", "results");

  await image(slide, ctx, "charts/optimization_ladder.png", 42, 144, 530, 330, "Optimization ladder");
  await image(slide, ctx, "charts/utilization_ladder.png", 602, 144, 530, 330, "Utilization ladder");

  metric(slide, ctx, "124.8x", "final speedup over baseline", 54, 508, 210, 88, colors.green);
  metric(slide, ctx, "1,184", "final cycle count", 284, 508, 210, 88, colors.blue);

  bulletList(slide, ctx, [
    "Early: remove bookkeeping and memory traffic.",
    "Middle: specialize the fixed workload and vectorize across the batch.",
    "Late: expose enough independent work for a VLIW scheduler to fill the machine."
  ], 610, 510, 480, { size: 14.5, gap: 42, bulletColor: colors.green });

  addFooter(slide, ctx, 13);
  return slide;
}
