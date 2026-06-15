import { addTitle, addFooter, bulletList, colors, image, metric } from "./common.mjs";

export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Specialization: Make The Fixed Workload Explicit", "Once the benchmark shape is known, the generated program can remove general-purpose control and layout handling.", "specialization");

  await image(slide, ctx, "trace_visuals/02_fixed_layout.png", 42, 150, 520, 230, "Fixed layout trace");
  await image(slide, ctx, "trace_visuals/03_unroll.png", 42, 410, 520, 230, "Unroll trace");

  metric(slide, ctx, "114,868 -> 110,898", "bake in fixed layout", 620, 158, 260, 95, colors.cyan);
  metric(slide, ctx, "110,898 -> 97,040", "unroll 16 known rounds", 900, 158, 250, 95, colors.cyan);

  bulletList(slide, ctx, [
    "Fixed layout: stable memory pointers and dimensions become constants instead of runtime setup.",
    "Round unrolling: the depth sequence is known, so the kernel emits the exact operation stream for all 16 rounds.",
    "Leaf behavior is predictable: after depth 10, traversal resets to root.",
    "Tradeoff: instruction file size grows, but this benchmark scores execution cycles."
  ], 626, 294, 494, { size: 14.5, gap: 58, bulletColor: colors.cyan });

  addFooter(slide, ctx, 8);
  return slide;
}
