import { addTitle, addFooter, box, bulletList, colors, image, label, metric } from "./common.mjs";

export async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Leveraging SIMD: Turn 256 Scalar Walks Into 32 Vector Groups", "Vectorization is the first structural change that dramatically changes the cycle curve.", "simd");

  await image(slide, ctx, "trace_visuals/04_vectorize.png", 42, 150, 700, 410, "Vectorization trace");

  metric(slide, ctx, "97,040 -> 12,285", "cycles after SIMD vectorization", 790, 156, 340, 96, colors.violet);
  box(slide, ctx, { x: 790, y: 284, w: 340, h: 112 });
  label(slide, ctx, "Batch geometry", 812, 306, 240, 24, { size: 18, bold: true });
  label(slide, ctx, "256 inputs / 8 SIMD lanes = 32 vector groups", 812, 344, 260, 38, { size: 16, color: colors.ink });

  bulletList(slide, ctx, [
    "The hash pipeline, value update, branch-bit calculation, and many index updates operate lane-wise.",
    "The trace shifts from scalar bookkeeping toward the VALU engine as the main workhorse.",
    "Narrative role: this is where hardware parallelism becomes central."
  ], 792, 430, 350, { size: 14.5, gap: 54, bulletColor: colors.violet });

  addFooter(slide, ctx, 9);
  return slide;
}
