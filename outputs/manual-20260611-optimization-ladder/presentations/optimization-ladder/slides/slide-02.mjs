import { addTitle, addFooter, bulletList, box, colors, label, metric } from "./common.mjs";

export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Background: A Compiler Challenge, Not Python Tuning", "Python emits a low-level program for a simulated CPU; the score is total simulator cycles.", "background");

  bulletList(slide, ctx, [
    "The take-home asks candidates to generate a correct kernel for a fixed workload and minimize cycle count.",
    "Correctness is checked against the reference problem; performance is measured by the simulator cycle counter.",
    "The interesting work is compiler work: code generation, specialization, memory placement, vectorization, dependency analysis, and scheduling.",
  ], 58, 154, 620, { size: 17, gap: 58 });

  box(slide, ctx, { x: 730, y: 146, w: 455, h: 360 });
  label(slide, ctx, "Anthropic Speed Thresholds", 754, 166, 300, 28, { size: 20, bold: true });
  const rows = [
    ["Baseline", "< 147,734", "#64748b"],
    ["Updated starter", "< 18,532", "#0891b2"],
    ["Opus 4 many hours", "< 2,164", "#7c3aed"],
    ["Best human-ish / casual", "< 1,790", "#7c3aed"],
    ["Advanced harnesses", "< 1,579 / 1,548 / 1,487 / 1,363", "#be123c"],
    ["This project", "1,184 cycles", "#16a34a"],
  ];
  rows.forEach((row, i) => {
    const y = 212 + i * 45;
    label(slide, ctx, row[0], 758, y, 210, 28, { size: 14, bold: true, color: row[2] });
    label(slide, ctx, row[1], 978, y, 176, 28, { size: 14, color: colors.ink, align: "right" });
  });

  metric(slide, ctx, "All thresholds", "final kernel passes every listed speed tier", 730, 536, 455, 92, colors.green);
  addFooter(slide, ctx, 2);
  return slide;
}
