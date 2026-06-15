import { addTitle, addFooter, bulletList, colors, image, metric } from "./common.mjs";

export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Baseline: The Trace Shows Serialization And Waste", "The starting point does correct work, but it leaves most available machine capacity unused.", "baseline");

  await image(slide, ctx, "trace_visuals/00_baseline.png", 42, 142, 760, 430, "Baseline trace visual");

  metric(slide, ctx, "147,734", "baseline cycles", 850, 152, 270, 95, colors.muted);
  bulletList(slide, ctx, [
    "Scalar execution dominates; vector lanes are largely unused.",
    "Index state repeatedly moves through memory even though it is only needed to choose future nodes.",
    "Loop/control overhead and address recomputation are visible before the useful tree-walk work.",
    "This trace established the first goal: remove bookkeeping before tuning deep scheduling."
  ], 850, 280, 310, { size: 14.5, gap: 56, bulletColor: colors.rose });

  addFooter(slide, ctx, 6);
  return slide;
}
