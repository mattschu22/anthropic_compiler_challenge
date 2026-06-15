import { addTitle, addFooter, box, bulletList, colors, image, label, metric } from "./common.mjs";

export async function slide12(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "A Better Scheduler: Pack Independent Ops Into VLIW Slots", "The final major gain comes from dependency-aware cross-engine scheduling.", "scheduling");

  await image(slide, ctx, "trace_visuals/08_vliw_schedule.png", 42, 145, 540, 230, "VLIW scheduling trace");
  await image(slide, ctx, "trace_visuals/09_final_refinements.png", 42, 405, 540, 230, "Final refinements trace");

  metric(slide, ctx, "8,884 -> 1,291", "global VLIW scheduling", 630, 150, 245, 92, colors.blue);
  metric(slide, ctx, "1,291 -> 1,184", "final scheduler refinements", 895, 150, 245, 92, colors.green);

  box(slide, ctx, { x: 630, y: 278, w: 510, h: 134 });
  label(slide, ctx, "Dependency hazards modeled by the scheduler", 654, 300, 340, 24, { size: 18, bold: true });
  label(slide, ctx, "RAW: consumer reads a value after producer writes it\nWAW: two writes to the same target must stay ordered\nWAR: later write must not clobber an earlier read", 654, 338, 430, 58, { size: 13.5, color: colors.ink, mono: true });

  bulletList(slide, ctx, [
    "Each operation gets read/write sets and an engine type.",
    "Ready operations are prioritized by critical path and packed under engine slot limits.",
    "Final refinements relax safe WAR hazards and use VALU-to-ALU fallback when vector lanes are saturated."
  ], 638, 450, 460, { size: 14, gap: 50, bulletColor: colors.blue });

  addFooter(slide, ctx, 12);
  return slide;
}
