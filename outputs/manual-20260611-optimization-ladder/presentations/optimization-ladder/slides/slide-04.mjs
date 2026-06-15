import { addTitle, addFooter, box, bulletList, colors, label } from "./common.mjs";

export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Machine Model And Perfetto Tooling", "The simulator behaves like a restricted VLIW/SIMD machine with separate execution engines.", "machine model");

  box(slide, ctx, { x: 52, y: 148, w: 560, h: 410 });
  label(slide, ctx, "Per-cycle engine slots", 78, 170, 300, 28, { size: 21, bold: true });
  const engines = [
    ["alu", "12", "scalar arithmetic, comparisons, address math"],
    ["valu", "6", "SIMD vector arithmetic, 8 lanes per instruction"],
    ["load", "2", "memory reads"],
    ["store", "2", "memory writes"],
    ["flow", "1", "conditional jumps / control"],
  ];
  engines.forEach((e, i) => {
    const y = 222 + i * 55;
    ctx.addShape(slide, { x: 78, y, w: 80, h: 36, fill: "#eff6ff", line: { fill: colors.faint, width: 1 } });
    label(slide, ctx, e[0], 96, y + 8, 44, 20, { size: 14, bold: true, color: colors.blue, align: "center" });
    label(slide, ctx, `${e[1]} slots`, 178, y + 8, 74, 20, { size: 14, bold: true });
    label(slide, ctx, e[2], 272, y + 8, 280, 24, { size: 13, color: colors.muted });
  });

  box(slide, ctx, { x: 670, y: 148, w: 505, h: 410 });
  label(slide, ctx, "How to read traces", 696, 170, 280, 28, { size: 21, bold: true });
  bulletList(slide, ctx, [
    "Rows are engine lanes; time moves left to right.",
    "Colored spans are issued operations.",
    "Blank gaps are idle capacity caused by dependencies, memory pressure, or lack of ready work.",
    "The goal is not simply fewer operations; it is denser useful work per cycle."
  ], 700, 222, 400, { size: 15.5, gap: 50, bulletColor: colors.violet });

  addFooter(slide, ctx, 4);
  return slide;
}
