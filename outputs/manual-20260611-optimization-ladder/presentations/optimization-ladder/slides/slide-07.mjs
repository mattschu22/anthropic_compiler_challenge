import { addTitle, addFooter, bulletList, colors, image, metric } from "./common.mjs";

export async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Easy Wins: Remove Ungraded And Unnecessary Work", "The first improvements come from aligning the kernel with exactly what the grader checks.", "remove work");

  await image(slide, ctx, "trace_visuals/00_baseline.png", 42, 150, 520, 230, "Baseline trace");
  await image(slide, ctx, "trace_visuals/01_remove_index_bookkeeping.png", 42, 410, 520, 230, "Remove index bookkeeping trace");

  metric(slide, ctx, "147,734 -> 114,868", "remove index bookkeeping", 620, 158, 360, 95, colors.green);

  bulletList(slide, ctx, [
    "Final values are graded; final index state is not. The last round can compute values without storing final indices.",
    "Live traversal indices still matter during execution, but they can live in scratch instead of memory between rounds.",
    "This combines the old test-contract and scratch-indices checkpoints because both remove index work from the graded path.",
    "Narrative role: these are low-risk cleanup passes before specialization."
  ], 626, 294, 494, { size: 14.5, gap: 58, bulletColor: colors.green });

  addFooter(slide, ctx, 7);
  return slide;
}
