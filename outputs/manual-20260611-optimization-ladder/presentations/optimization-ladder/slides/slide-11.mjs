import { addTitle, addFooter, box, bulletList, colors, image, label, metric } from "./common.mjs";

export async function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Exposing Independent Work: Temporary Banks", "The scheduler can only pack operations that look independent in scratch/register space.", "parallel work");

  await image(slide, ctx, "trace_visuals/06_streaming_io.png", 42, 148, 500, 220, "Before temp banks trace");
  await image(slide, ctx, "trace_visuals/07_temp_banks.png", 42, 408, 500, 220, "After temp banks trace");

  metric(slide, ctx, "11,825 -> 8,884", "cycles after temp banks and local packing", 608, 150, 350, 95, colors.rose);

  box(slide, ctx, { x: 608, y: 282, w: 500, h: 130 });
  label(slide, ctx, "Why temp banks matter", 632, 302, 260, 24, { size: 18, bold: true });
  label(slide, ctx, "If unrelated vector groups reuse the same scratch names, dependency analysis treats them as serialized. Multiple temp banks give independent groups separate names so more operations can be ready at the same time.", 632, 338, 430, 58, { size: 14, color: colors.ink });

  bulletList(slide, ctx, [
    "This is not yet the global VLIW scheduler.",
    "It prepares the program so a real scheduler has enough independent work to choose from.",
    "Narrative role: separate algorithmic parallelism from whether the generated code exposes that parallelism."
  ], 614, 450, 450, { size: 14.5, gap: 50, bulletColor: colors.rose });

  addFooter(slide, ctx, 11);
  return slide;
}
